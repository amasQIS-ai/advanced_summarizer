import os
import io
import base64
import requests
import traceback
from typing import Literal

import yaml
import streamlit as st
from bs4 import BeautifulSoup
from google.genai import types
import streamlit_authenticator as stauth

import prompts
from utils import summarize_common

# ==============================================================
# 1. SET PAGE CONFIG BEFORE ANYTHING ELSE!
#    (We use wide layout + custom page title/icon)
# ==============================================================
st.set_page_config(
    page_title="SummarizeIQ",
    page_icon="📄",
    layout="centered"
)

# ==============================================================
# 2. APPLY CUSTOM CSS (optional)
#    You can add or modify any custom styling here
# ==============================================================
def apply_custom_css():
    st.markdown(
        """
        <style>
        
        /* Center the logo container */
        .logo-container {
            display: flex;
            justify-content: center;
            margin: 1rem 0 2rem 0;
        }
        .logo-container img {
            width: 80px; /* control the size of the logo here */
            height: auto;
        }
        .p {
            font-color: Green;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

apply_custom_css()
with open("assets/logo.png", "rb") as f:
    logo_data = f.read()
logo_base64 = base64.b64encode(logo_data).decode("utf-8")
st.markdown(
        f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo">
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------
# Now your Summarizer interface
# -----------------------------

# We create a simple literal type for doc_type (optional)
DocumentType = Literal["Research paper", "Literature Review", "Report"]

# # Add a responsive logo at the top (already in custom CSS)
# with open("assets/logo.png", "rb") as f:
#     logo_data = f.read()
# logo_base64 = base64.b64encode(logo_data).decode("utf-8")
# st.markdown(
#     f"""
#     <div class="logo-container">
#         <img src="data:image/png;base64,{logo_base64}" alt="Logo">
#     </div>
#     """,
#     unsafe_allow_html=True
# )

st.title("SummarizeIQ")
st.write(
    """
    This application summarizes PDF content or URLs (webpages, articles, etc.).
    Please select one of the tabs below to use the corresponding feature.
    """
)

# -------------------------------------------------------------------------
# Helper function to extract text and images from a URL (Gemini image desc)
# -------------------------------------------------------------------------
def extract_text_and_images_from_url(url: str) -> list[types.Part]:
    """
    Extract text and images from a web article URL.
    Uses Google Gemini to describe each image found (if any).
    Returns:
        text_content (str): extracted textual content (article text).
        image_descriptions (List[str]): descriptions of each image.
    """
    parts = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/94.0.4606.81 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error(f"Failed to fetch the page. Status code: {response.status_code}")
        return []

    html = response.content
    soup = BeautifulSoup(html, 'html.parser')

    # Try to find the main <article> tag; fallback to entire page
    article = soup.find('article')
    if article:
        text_content = article.get_text()
    else:
        text_content = soup.get_text()
    
    text_part = types.Part.from_text(text=text_content)
    parts.append(text_part)

    # Find all <img> tags
    images = soup.find_all('img')
    for image in images:
        img_url = image.get('src')
        if img_url and not img_url.startswith('data:'):
            img_url = requests.compat.urljoin(url, img_url)  # handle relative URLs
            img_response = requests.get(img_url, headers=headers)
            if img_response.status_code == 200:
                image_bytes = io.BytesIO(img_response.content)
                # Convert to base64 so we can pass it as a Part to Gemini
                image_base64 = base64.b64encode(image_bytes.getvalue()).decode("utf-8")

                # Summarize the image using the same "summarize_common" method
                image_part = types.Part.from_bytes(
                    data=base64.b64decode(image_base64),
                    mime_type="image/png"  # or "image/jpeg", depending on actual img
                )
                parts.append(image_part)

    # Fallback if no images or no text
    if not parts:
        st.error("No valid data found.")
    return parts

# Create tabs in the Streamlit UI
tab1, tab2 = st.tabs(["Summarize PDF", "Summarize URL"])

# -------------------------------------
# 1. Summarize PDF
# -------------------------------------
with tab1:
    st.subheader("Upload and Summarize a PDF")
    st.success(""" 
                Recommended:
                1. Please upload a PDF file (maximum size: 15 MB).
                2. For optimal results, upload a PDF with 30 pages or fewer.
                """ )

    # Select the document type
    doc_type: DocumentType = st.selectbox(
        "Select Document Type",
        ("Research paper", "Literature Review", "Report"),
        index=0
    )

    # File uploader for PDF
    uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

    # Button to trigger summarization
    if st.button("Summarize PDF"):
        if uploaded_file is None:
            st.error("Please upload a PDF file first.")
        else:
            # Check if the uploaded file is a PDF
            if not uploaded_file.name.lower().endswith(".pdf"):
                st.error("Only PDF files are allowed.")
            else:
                # Check if the file size exceeds 15 MB
                uploaded_file.seek(0, 2)  # Move cursor to the end of the file
                file_size = uploaded_file.tell()
                uploaded_file.seek(0)     # Reset cursor to the start

                if file_size > 15 * 1024 * 1024:
                    st.error("File size too big. Maximum allowed size is 15 MB.")
                else:
                    try:
                        # Read the content of the file
                        content = uploaded_file.read()
                        # Encode to base64
                        base64_pdf = base64.b64encode(content)
                        
                        # Convert base64 back to bytes
                        document_part = types.Part.from_bytes(
                            data=base64.b64decode(base64_pdf),
                            mime_type="application/pdf"
                        )

                        # Use the appropriate prompts
                        if doc_type == "Research paper":
                            assitant_prompt_part = types.Part.from_text(text=prompts.research_paper_prompt)

                            completion_string = summarize_common(
                                system_prompt=prompts.system_prompt.format(document_name=doc_type),
                                parts=[assitant_prompt_part, document_part]
                            )
                        elif doc_type == "Literature Review":
                            assitant_prompt_part = types.Part.from_text(text=prompts.literature_review_prompt)
                            completion_string = summarize_common(
                                system_prompt=prompts.system_prompt.format(document_name=doc_type),
                                parts=[assitant_prompt_part, document_part]
                            )
                        else:  # "Report"
                            assitant_prompt_part = types.Part.from_text(text=prompts.report_prompt)
                            completion_string = summarize_common(
                                system_prompt=prompts.system_prompt.format(document_name=doc_type),
                                parts=[assitant_prompt_part, document_part]
                            )

                        # Display the summarized content
                        st.success("Summary generated successfully!")
                        st.write(completion_string)  
                        st.download_button(f"Download {doc_type} Summary", completion_string, file_name=f"{doc_type}.md")
                    except Exception as e:
                        st.error(f"An error occurred")
                        traceback.print_exc()

# -------------------------------------
# 2. Summarize URL (Extract Text & Images)
# -------------------------------------
with tab2:
    st.subheader("Summarize a Webpage by URL")
    st.warning("This summarizer is under beta testing.The summarization may not be accurate.")

    url = st.text_input("Enter a URL", placeholder="https://example.com/article")

    if st.button("Summarize URL"):
        if not url:
            st.error("Please enter a valid URL.")
        else:
            try:
                assitant_prompt_part = types.Part.from_text(text=prompts.article_prompt)
                # Extract text & images directly
                parts = extract_text_and_images_from_url(url)

                if parts:
                    total_parts = [assitant_prompt_part]+parts
                    # Summarize using the 'article_prompt'
                    completion_string = summarize_common(
                        system_prompt=prompts.system_prompt.format(document_name="article"),
                        parts=total_parts
                    )

                    st.success("Summary generated successfully!")
                    st.write(completion_string)
                    st.download_button("Download Article Summary", completion_string, file_name="Article summary.md")
                else:
                    st.error("No valid data found.")

            except Exception as e:
                st.error(f"An error occurred. Try a different URL.")
                traceback.print_exc()
