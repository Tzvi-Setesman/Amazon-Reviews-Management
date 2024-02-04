import streamlit as st
import pandas as pd
from collections import Counter
import os
import base64
import re
import shutil
import time
from nltk.corpus import wordnet

# Decorator function to measure and display the execution time of functions
def timer_function(func):
    """
    Decorator to measure and display the execution time of a function.
    
    Args:
        func (function): The function to measure.
    
    Returns:
        function: A wrapper function that measures execution time.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        st.write(f"{func.__name__.replace('_', ' ').capitalize()} completed in {end_time - start_time:.2f} seconds.")
        return result
    return wrapper

# Load data from CSV files, cache the result to avoid reloading on every interaction
@st.cache(allow_output_mutation=True, suppress_st_warning=True)
@timer_function
def load_data(file_paths):
    """
    Load data from a list of CSV files into a single DataFrame.
    
    Args:
        file_paths (list of str): Paths to the CSV files.
    
    Returns:
        pandas.DataFrame: Combined DataFrame from all files.
    """
    data_frames = [pd.read_csv(file_path, names=["polarity", "title", "text"]) for file_path in file_paths]
    return pd.concat(data_frames)

# Filter data by sentiment, positive or negative
@st.cache(allow_output_mutation=True, suppress_st_warning=True)
@timer_function
def filter_data_by_sentiment(data, sentiment):
    """
    Filter the DataFrame by sentiment (positive or negative).
    
    Args:
        data (pandas.DataFrame): The DataFrame to filter.
        sentiment (str): 'positive' or 'negative'.
    
    Returns:
        pandas.DataFrame: Filtered DataFrame.
    """
    sentiment_mapping = {'positive': 2, 'negative': 1}
    return data[data["polarity"] == sentiment_mapping[sentiment]]

# Find and filter data by similar words using NLTK's WordNet
@st.cache(allow_output_mutation=True, suppress_st_warning=True)
@timer_function
def find_similar_words(data, search_word):
    """
    Find similar words to a given word and filter the DataFrame by these words.
    
    Args:
        data (pandas.DataFrame): The DataFrame to filter.
        search_word (str): The word to find synonyms for.
    
    Returns:
        tuple: Filtered DataFrame and list of synonyms.
    """
    synonyms = []
    if search_word:
        synonyms = [lemma.name() for syn in wordnet.synsets(search_word) for lemma in syn.lemmas()]
        data = data[data['text'].str.contains('|'.join(synonyms), case=False)]
    return data, synonyms

# Generate a list of the most common words in the data
@timer_function
def generate_word_cloud(data):
    """
    Generate a list of the most common words in the data.
    
    Args:
        data (pandas.DataFrame): The DataFrame to analyze.
    
    Returns:
        list: List of the most common words.
    """
    text = data['text'].str.cat(sep=' ')
    words = re.findall(r'\w+', text)
    word_count = Counter(words)
    common_words = word_count.most_common(20)
    return [word for word, count in common_words]

# Create one or more Excel files from the data, considering maximum row limitations
@timer_function
def create_single_excel(data, max_rows=250000):
    """
    Create one or more Excel files from the DataFrame, considering Excel's maximum row limitations.
    
    Args:
        data (pandas.DataFrame): The DataFrame to export.
        max_rows (int, optional): Maximum rows per Excel file. Defaults to 250000.
    
    Returns:
        list: Paths to the created Excel files.
    """
    temp_dir = 'temp_excel'
    os.makedirs(temp_dir, exist_ok=True)
    file_paths = []

    chunk_size = 750000  # Adjust based on the maximum size for readability

    for i in range(0, len(data), chunk_size):
        file_name = f'data_part_{i // chunk_size + 1}.xlsx'
        file_path = os.path.join(temp_dir, file_name)
        chunk_data = data.iloc[i:i + chunk_size]
        if len(chunk_data) > max_rows:
            chunk_data = chunk_data[:max_rows]
        chunk_data.to_excel(file_path, index=False, engine='xlsxwriter')
        file_paths.append(file_path)

    return file_paths

# Function to clean up temporary Excel files after download
@timer_function
def clean_temp_files(temp_dir='temp_excel'):
    """
    Clean up temporary Excel files.
    
    Args:
        temp_dir (str, optional): The directory to clean. Defaults to 'temp_excel'.
    """
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
