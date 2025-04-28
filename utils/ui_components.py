import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_manager import save_data
from utils.link_operations import save_link, delete_selected_links, fetch_metadata, process_bookmark_file
import logging
from io import BytesIO
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
import time
import uuid

def apply_css():
    """Apply CSS for consistent color scheme across the app"""
    css = """
    <style>
    /* Base styles */
    .header-admin, .header-guest, .header-public {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .header-admin { background-color: #7a97e8 !important; } /* Light blue for admin */
    .header-guest { background-color: #F0FFFF !important; } /* Light parrot green for guest */
    .header-public { background-color: #CCCCFF !important; } /* Light purple for public */
    .login-container {
        background-color: #DA70D6 !important; /* Orchid */
        padding: 2rem;
        border-radius: 8px;
        text-align: center;
    }
    .button-tooltip {
        position: relative;
    }
    .button-tooltip:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        background-color: #333;
        color: white;
        padding: 0.5rem;
        border-radius: 4px;
        z-index: 10;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        white-space: nowrap;
    }

    /* Responsive design */
    @media (max-width: 768px) {
        .stForm, .stDataFrame {
            font-size: 14px;
        }
        .stButton > button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        .stDataFrame {
            overflow-x: auto;
        }
    }

    /* Debug CSS application */
    .debug-css::after {
        content: "CSS Loaded";
        display: none;
    }
    </style>
    <div class="debug-css"></div>
    """
    st.markdown(css, unsafe_allow_html=True)

def display_header(mode, username=None):
    """Display the app header with mode-specific styling and logout button"""
    apply_css()  # Ensure CSS is applied
    header_class = f"header-{mode}"
    logging.debug(f"Displaying header: mode={mode}, username={username}")
    st.markdown(f"""
    <div class="{header_class}">
        <h1 style="margin: 0;">Web Content Manager</h1>
        <p style="margin: 0.5rem 0 0;">Organize and manage your web links efficiently</p>
        <p style="margin: 0.5rem 0 0;">{mode.capitalize()} Mode{f" ({username})" if username else ""}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Logout", help="Log out and return to login screen"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ Logged out successfully!")
        st.snow()
        time.sleep(2)
        st.rerun()

# ... (rest of the file remains unchanged)
