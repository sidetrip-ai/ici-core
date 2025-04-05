import re
from typing import List, Optional, Union
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

class TextPreprocessor:
    """Text preprocessing utilities for cleaning and normalizing text."""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by removing special characters, extra whitespace, etc.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and digits
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def remove_stopwords(self, text: str) -> str:
        """
        Remove common stopwords from text.
        
        Args:
            text: Input text
            
        Returns:
            Text with stopwords removed
        """
        words = word_tokenize(text)
        filtered_words = [word for word in words if word.lower() not in self.stop_words]
        return ' '.join(filtered_words)
    
    def lemmatize_text(self, text: str) -> str:
        """
        Lemmatize text to reduce words to their base form.
        
        Args:
            text: Input text
            
        Returns:
            Lemmatized text
        """
        words = word_tokenize(text)
        lemmatized_words = [self.lemmatizer.lemmatize(word) for word in words]
        return ' '.join(lemmatized_words)
    
    def split_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks for better processing.
        
        Args:
            text: Input text
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            
            # If this is not the last chunk, try to break at a sentence boundary
            if end < text_len:
                # Find the last sentence boundary within the chunk
                sentences = sent_tokenize(text[start:end + overlap])
                if len(sentences) > 1:
                    # Use all but the last sentence
                    chunk_text = ' '.join(sentences[:-1])
                    # Update start position for next chunk
                    start += len(chunk_text)
                else:
                    # If no sentence boundary found, just use the chunk as is
                    chunk_text = text[start:end]
                    start = end
            else:
                # Last chunk, use remaining text
                chunk_text = text[start:]
                start = text_len
            
            chunks.append(chunk_text.strip())
        
        return chunks
    
    def process_text(self, text: str, clean: bool = True, remove_stops: bool = True, 
                    lemmatize: bool = True, chunk_size: Optional[int] = None) -> Union[str, List[str]]:
        """
        Process text with selected preprocessing steps.
        
        Args:
            text: Input text
            clean: Whether to clean the text
            remove_stops: Whether to remove stopwords
            lemmatize: Whether to lemmatize
            chunk_size: Optional chunk size for splitting text
            
        Returns:
            Processed text (or list of chunks if chunk_size is specified)
        """
        if clean:
            text = self.clean_text(text)
        
        if remove_stops:
            text = self.remove_stopwords(text)
        
        if lemmatize:
            text = self.lemmatize_text(text)
        
        if chunk_size:
            return self.split_into_chunks(text, chunk_size)
        
        return text 