import streamlit as st
import pandas as pd
from collections import Counter
import os
import base64
import re
import shutil
import time
from nltk.corpus import wordnet
import nltk


try:
    nltk.download('wordnet')
    st.success("NLTK Wordnet downloaded successfully!")
except LookupError:
    st.error("Failed to download NLTK Wordnet. Please check your internet connection or NLTK installation.")

Max rows allowed in a single Excel sheet
MAX_ROWS_PER_SHEET = 1048576

def timer_function(func):
    """
    Decorator to measure the execution time of a function.

    Parameters:
    - func: The function to be wrapped by the timer.

    Returns:
    - wrapper function that prints the execution time.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        st.write(f"{func.__name__.replace('_', ' ').capitalize()} completed in {end_time - start_time:.2f} seconds.")
        return result
    return wrapper

@st.cache(allow_output_mutation=True, suppress_st_warning=True)
@timer_function
def load_data(file_paths):
    """
    Load and concatenate CSV files into a single pandas DataFrame.

    Parameters:
    - file_paths (list of str): Paths to the CSV files to load.

    Returns:
    - A pandas DataFrame containing all rows from the loaded CSV files.
    """
    data_frames = [pd.read_csv(file_path, names=["polarity", "title", "text"]) for file_path in file_paths]
    return pd.concat(data_frames)

@st.cache(allow_output_mutation=True, suppress_st_warning=True)
@timer_function
def filter_data_by_sentiment(data, sentiment):
    """
    Filter data by sentiment (positive or negative).

    Parameters:
    - data (pd.DataFrame): The DataFrame to filter.
    - sentiment (str): The sentiment to filter by ('positive' or 'negative').

    Returns:
    - A filtered pandas DataFrame.
    """
    sentiment_mapping = {'positive': 2, 'negative': 1}
    return data[data["polarity"] == sentiment_mapping[sentiment]]

@st.cache_data
@timer_function
def find_similar_words(data, search_word):
    """
    Find reviews containing words similar to the specified search word.

    Parameters:
    - data (pd.DataFrame): The DataFrame to search within.
    - search_word (str): The word to find similar words for.

    Returns:
    - Tuple of (filtered pandas DataFrame, list of similar words).
    """
    synonyms = []
    if search_word:
        synonyms = [lemma.name() for syn in wordnet.synsets(search_word) for lemma in syn.lemmas()]
        data = data[data['text'].str.contains('|'.join(synonyms), case=False)]
    return data, synonyms

@timer_function
def generate_word_cloud(data):
    """
    Generate a list of the most common words in the data.

    Parameters:
    - data (pd.DataFrame): The DataFrame from which to generate the word cloud.

    Returns:
    - A list of the most common words.
    """
    text = data['text'].str.cat(sep=' ')
    words = re.findall(r'\w+', text)
    word_count = Counter(words)
    common_words = word_count.most_common(20)
    return [word for word, count in common_words]

@timer_function
def create_single_excel(data):
    """
    Create a single Excel file from the given data.

    Parameters:
    - data (pd.DataFrame): The DataFrame to export to Excel.

    Returns:
    - The file path of the created Excel file.
    """
    temp_dir = 'temp_excel'
    os.makedirs(temp_dir, exist_ok=True)
    
    excel_file_name = 'data.xlsx'
    excel_file_path = os.path.join(temp_dir, excel_file_name)
    data.to_excel(excel_file_path, index=False, engine='xlsxwriter')
    
    return excel_file_path

def get_download_link(file_path, label='Download Excel File'):
    """
    Generate a download link for the given file.

    Parameters:
    - file_path (str): The path to the file to download.
    - label (str): The text of the download link.

    Returns:
    - An HTML <a> tag as a string for the download link.
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{bin_str}" download="{os.path.basename(file_path)}">{label}</a>'
    return href

def main():
    """
    The main function to run the Streamlit app.
    """
    st.title('Amazon Reviews Management')
    sentiment = st.sidebar.radio('Sentiment Type', ('positive', 'negative'))

    if 'loaded_data' not in st.session_state:
        file_paths = ["a.csv", "b.csv"]
        st.session_state.loaded_data = load_data(file_paths)
        st.write(f"Total rows loaded: {len(st.session_state.loaded_data)}")

    if st.sidebar.button('Filter Data'):
        st.session_state.filtered_data = filter_data_by_sentiment(st.session_state.loaded_data.copy(), sentiment)
        st.write(f"Total rows after filtering: {len(st.session_state.filtered_data)}")

    if 'filtered_data' in st.session_state and not st.session_state.filtered_data.empty:
        if st.sidebar.button('Export to Excel'):
            file_path = create_single_excel(st.session_state.filtered_data)
            st.write("Download Excel file:")
            st.markdown(get_download_link(file_path, 'Download Excel File'), unsafe_allow_html=True)

        search_word = st.text_input('Enter a word to find similar words:')
        if st.button('Find Similar Words'):
            st.session_state.filtered_data, synonyms = find_similar_words(st.session_state.filtered_data, search_word)
            if synonyms:
                st.write(', '.join(synonyms))
                common_words = generate_word_cloud(st.session_state.filtered_data)
                st.write('Popular words:')
                with st.expander("See words"):
                    st.write(", ".join(common_words))
            else:
                st.warning('No synonyms found.')

        page_size = st.sidebar.slider('Rows per page', 1, 100, 5)
        page_number = st.sidebar.number_input('Page number', 1, max(1, len(st.session_state.filtered_data) // page_size) + 1, 1)
        st.write(f"Displaying rows {page_number * page_size - page_size + 1} to {min(page_number * page_size, len(st.session_state.filtered_data))} out of {len(st.session_state.filtered_data)}")

        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size

        st.table(st.session_state.filtered_data.iloc[start_idx:end_idx])

    else:
        st.sidebar.write("No data loaded or filtered yet.")

if __name__ == '__main__':
    main()
