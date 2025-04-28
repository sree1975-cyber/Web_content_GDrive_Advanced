import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from newspaper import Article
import logging
import uuid
from datetime import datetime
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
import re
import os

def fetch_metadata(url):
    """Fetch metadata for a given URL with fallback handling"""
    try:
        article = Article(url, fetch_images=False)
        article.download()
        article.parse()
        title = article.title or ""
        description = article.meta_description or article.text[:200] or ""
        
        if not title or not description:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc['content'] if meta_desc else ""
        
        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(f"{title} {description}")
            tags = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2]
            tags = list(set(tags))[:5]
        except Exception as e:
            logging.error(f"Failed to load spaCy model: {str(e)}")
            tags = []
        
        logging.debug(f"Fetched metadata for {url}: Title={title[:50]}, Description={description[:50]}, Tags={tags}")
        return {"title": title, "description": description, "tags": tags}
    except Exception as e:
        logging.error(f"Metadata fetch failed for {url}: {str(e)}")
        return {"title": "", "description": "", "tags": []}

def save_link(df, url, title, description, tags, priority, number, mode):
    """Save a new link to the DataFrame"""
    try:
        required_columns = [
            "link_id", "url", "title", "description", "tags",
            "created_at", "updated_at", "priority", "number", "is_duplicate"
        ]
        if df.empty:
            df = pd.DataFrame(columns=required_columns)
        
        is_duplicate = url in df["url"].values
        
        new_row = {
            "link_id": str(uuid.uuid4()),
            "url": url,
            "title": title,
            "description": description,
            "tags": tags if isinstance(tags, list) else [tags],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "priority": priority,
            "number": number,
            "is_duplicate": is_duplicate
        }
        
        new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        logging.debug(f"Saved link: {url}, Duplicate={is_duplicate}")
        return new_df
    except Exception as e:
        logging.error(f"Failed to save link {url}: {str(e)}")
        return None

def delete_selected_links(df, link_ids, excel_file, mode):
    """Delete selected links from the DataFrame"""
    try:
        updated_df = df[~df["link_id"].isin(link_ids)].copy()
        if mode in ["admin", "guest"] and excel_file:
            from utils.data_manager import save_data
            save_data(updated_df, excel_file)
        logging.debug(f"Deleted {len(df) - len(updated_df)} links")
        return updated_df
    except Exception as e:
        logging.error(f"Failed to delete links: {str(e)}")
        return df

def process_bookmark_file(df, uploaded_file, mode, duplicate_action, progress_bar):
    """Process uploaded bookmark file"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == "xlsx":
            new_data = pd.read_excel(uploaded_file)
        elif file_extension == "csv":
            new_data = pd.read_csv(uploaded_file)
        elif file_extension == "html":
            soup = BeautifulSoup(uploaded_file, 'html.parser')
            links = soup.find_all('a')
            new_data = pd.DataFrame({
                "url": [link.get('href') for link in links],
                "title": [link.text for link in links],
                "description": ["" for _ in links],
                "tags": [[] for _ in links]
            })
        else:
            raise ValueError("Unsupported file format")
        
        new_data = new_data.rename(columns={
            "URL": "url", "Link": "url", "href": "url",
            "Title": "title", "Name": "title",
            "Description": "description", "Notes": "description",
            "Tags": "tags", "Keywords": "tags"
        })
        
        for col in ["url", "title", "description", "tags"]:
            if col not in new_data.columns:
                new_data[col] = "" if col != "tags" else []
        
        new_data["tags"] = new_data["tags"].apply(lambda x: x.split(',') if isinstance(x, str) else x if isinstance(x, list) else [])
        
        new_data["link_id"] = [str(uuid.uuid4()) for _ in range(len(new_data))]
        new_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_data["priority"] = "Low"
        new_data["number"] = 0
        new_data["is_duplicate"] = False
        
        if duplicate_action == "Skip Duplicates":
            new_data = new_data[~new_data["url"].isin(df["url"])]
        
        new_data["is_duplicate"] = new_data["url"].isin(df["url"])
        
        updated_df = pd.concat([df, new_data], ignore_index=True)
        
        progress_bar.progress(1.0)
        logging.debug(f"Processed bookmark file: {len(new_data)} new links")
        return updated_df
    except Exception as e:
        logging.error(f"Failed to process bookmark file: {str(e)}")
        return df
