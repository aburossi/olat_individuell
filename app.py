import streamlit as st
from openai import OpenAI
import json
import random
import PyPDF2
import docx
import re
import base64
from pdf2image import convert_from_bytes
import io
from PIL import Image
import logging
import streamlit.components.v1 as components
import httpx
import os
import zipfile
import tempfile

# Logging for better error tracking
logging.basicConfig(level=logging.INFO)

# Set page configuration and enforce Light Mode
st.set_page_config(
    page_title="📝 OLAT Fragen Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enforce Light Mode using CSS
st.markdown(
    """
    <style>
    /* Force light mode */
    body, .css-18e3th9, .css-1d391kg {
        background-color: white;
        color: black;
    }
    /* Override Streamlit's default dark mode elements */
    .css-1aumxhk, .css-1v3fvcr {
        background-color: white;
    }
    /* Ensure all text is dark */
    .css-1v0mbdj, .css-1xarl3l {
        color: black;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# App Title
st.title("📝 Fragen Generator")

# Sidebar for Instructions and Additional Information
with st.sidebar:
    st.header("❗ **So verwenden Sie diese App**")
    
    st.markdown("""
    1. **Geben Sie Ihren OpenAI-API-Schlüssel ein**: Erhalten Sie Ihren API-Schlüssel von [OpenAI](https://platform.openai.com/account/api-keys) und geben Sie ihn im Feld *OpenAI-API-Schlüssel* ein.
    """)
    
    # Embed YouTube Video in Sidebar
    components.html("""
        <iframe width="100%" height="180" src="https://www.youtube.com/embed/NsTAjBdHb1k" 
        title="Demo-Video auf Deutsch" frameborder="0" allow="accelerometer; autoplay; 
        clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
        </iframe>
    """, height=180)
    
    # Additional Instructions
    st.markdown("""
    2. **Laden Sie eine oder mehrere PDF, DOCX oder Bilddateien hoch**: Wählen Sie Dateien von Ihrem Computer aus.
    3. **Sprache auswählen**: Wählen Sie die gewünschte Sprache für die generierten Fragen.
    4. **Fragetypen auswählen**: Wählen Sie die Typen der Fragen, die Sie generieren möchten.
    5. **Fragen generieren**: Klicken Sie auf die Schaltfläche "Fragen generieren", um den Prozess zu starten.
    6. **Generierte Inhalte herunterladen**: Nach der Generierung können Sie die Antworten herunterladen.
    """)
    
    # Cost Information and Question Type Explanations
    st.markdown('''
    <div class="custom-info">
        <strong>ℹ️ Kosteninformationen:</strong>
        <ul>
            <li>Die Nutzungskosten hängen von der <strong>Länge der Eingabe</strong> ab (zwischen 0,01 $ und 0,1 $).</li>
            <li>Jeder ausgewählte Fragetyp kostet ungefähr 0,01 $.</li>
        </ul>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('''
    <div class="custom-success">
        <strong>✅ Multiple-Choice-Fragen:</strong>
        <ul>
            <li>Alle Multiple-Choice-Fragen haben maximal 3 Punkte.</li>
            <li><strong>multiple_choice1</strong>: 1 von 4 richtigen Antworten.</li>
            <li><strong>multiple_choice2</strong>: 2 von 4 richtigen Antworten.</li>
            <li><strong>multiple_choice3</strong>: 3 von 4 richtigen Antworten.</li>
        </ul>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('''
    <div class="custom-success">
        <strong>✅ Inline/FIB-Fragen:</strong>
        <ul>
            <li>Die <strong>Inline</strong> und <strong>FIB</strong> Fragen sind inhaltlich identisch.</li>
            <li>FIB = fehlendes Wort eingeben.</li>
            <li>Inline = fehlendes Wort auswählen.</li>
        </ul>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('''
    <div class="custom-success">
        <strong>✅ Andere Fragetypen:</strong>
        <ul>
            <li><strong>Single Choice</strong>: 4 Antworten, 1 Punkt pro Frage.</li>
            <li><strong>KPRIM</strong>: 4 Antworten, 5 Punkte (4/4 korrekt), 2,5 Punkte (3/4 korrekt), 0 Punkte (50% oder weniger korrekt).</li>
            <li><strong>True/False</strong>: 3 Antworten, 3 Punkte pro Frage.</li>
            <li><strong>Drag & Drop</strong>: Variable Punkte.</li>
        </ul>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('''
    <div class="custom-warning">
        <strong>⚠️ Warnungen:</strong>
        <ul>
            <li><strong>Überprüfen Sie immer, dass die Gesamtpunkte = Summe der Punkte der korrekten Antworten sind.</strong></li>
            <li><strong>Überprüfen Sie immer den Inhalt der Antworten.</strong></li>
        </ul>
    </div>
    ''', unsafe_allow_html=True)

    # Separator and License Information
    st.markdown("---")
    st.header("📜 Lizenz")
    st.markdown("""
    Diese Anwendung steht unter der [MIT-Lizenz](https://opensource.org/licenses/MIT). 
    Sie dürfen diese Software verwenden, ändern und weitergeben, solange die ursprüngliche Lizenz beibehalten wird.
    """)

    # Contact Information
    st.header("💬 Kontakt")
    st.markdown("""
    Für Unterstützung, Fragen oder um mehr über die Nutzung dieser App zu erfahren, kannst du gerne auf mich zukommen.
    **Kontakt**: [Pietro](mailto:pietro.rossi@bbw.ch)
    """)

# Streamlit Widgets for API Key Input
st.header("🔑 Geben Sie Ihren OpenAI-API-Schlüssel ein")
api_key = st.text_input("OpenAI-API-Schlüssel:", type="password")

# Clear any existing proxy environment variables to prevent OpenAI SDK from using them
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# Initialize a custom httpx client without proxies
http_client = httpx.Client()

# Initialize OpenAI client if an API key is provided
client = None
if api_key:
    try:
        client = OpenAI(
            api_key=api_key,
            http_client=http_client
        )
        st.success("API-Schlüssel erfolgreich erkannt und verbunden.")
    except Exception as e:
        st.error(f"Fehler bei der Initialisierung des OpenAI-Clients: {e}")

# List of Available Question Types
MESSAGE_TYPES = [
    "single_choice",
    "multiple_choice1",
    "multiple_choice2",
    "multiple_choice3",
    "kprim",
    "truefalse",
    "draganddrop",
    "inline_fib"
]

@st.cache_data
def read_prompt_from_md(filename):
    """Reads the prompt from a Markdown file and caches the result."""
    with open(f"{filename}.md", "r", encoding="utf-8") as file:
        return file.read()

def process_image(_image):
    """Processes and resizes an image to reduce memory usage."""
    if isinstance(_image, (str, bytes)):
        img = Image.open(io.BytesIO(base64.b64decode(_image) if isinstance(_image, str) else _image))
    elif isinstance(_image, Image.Image):
        img = _image
    else:
        img = Image.open(_image)

    # Convert to RGB mode if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize if the image is too large
    max_size = 1000  # Reduced maximum size to lower memory usage
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))

    # Save to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    return base64.b64encode(img_byte_arr).decode('utf-8')

def replace_german_sharp_s(text):
    """Replaces all occurrences of 'ß' with 'ss'."""
    return text.replace('ß', 'ss')


def clean_json_string(s):
    s = s.strip()
    s = re.sub(r'^```json\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'(?<=text": ")(.+?)(?=")', lambda m: m.group(1).replace('\n', '\\n'), s)
    s = ''.join(char for char in s if ord(char) >= 32 or char == '\n')
    match = re.search(r'\[.*\]', s, re.DOTALL)
    return match.group(0) if match else s

def convert_json_to_text_format(json_input):
    if isinstance(json_input, str):
        data = json.loads(json_input)
    else:
        data = json_input

    fib_output = []
    ic_output = []

    for item in data:
        text = item.get('text', '')
        blanks = item.get('blanks', [])
        wrong_substitutes = item.get('wrong_substitutes', [])

        num_blanks = len(blanks)

        fib_lines = [
            "Type\tFIB",
            "Title\t✏✏Vervollständigen Sie die Lücken mit dem korrekten Begriff.✏✏",
            f"Points\t{num_blanks}"
        ]

        for blank in blanks:
            text = text.replace(blank, "{blank}", 1)

        parts = text.split("{blank}")
        for index, part in enumerate(parts):
            fib_lines.append(f"Text\t{part.strip()}")
            if index < len(blanks):
                fib_lines.append(f"1\t{blanks[index]}\t20")

        fib_output.append('\n'.join(fib_lines))

        ic_lines = [
            "Type\tInlinechoice",
            "Title\tWörter einordnen",
            "Question\t✏✏Wählen Sie die richtigen Wörter.✏✏",
            f"Points\t{num_blanks}"
        ]

        all_options = blanks + wrong_substitutes
        random.shuffle(all_options)

        for index, part in enumerate(parts):
            ic_lines.append(f"Text\t{part.strip()}")
            if index < len(blanks):
                options_str = '|'.join(all_options)
                ic_lines.append(f"1\t{options_str}\t{blanks[index]}\t|")

        ic_output.append('\n'.join(ic_lines))

    return '\n\n'.join(fib_output), '\n\n'.join(ic_output)

def transform_output(json_string):
    try:
        cleaned_json_string = clean_json_string(json_string)
        json_data = json.loads(cleaned_json_string)
        fib_output, ic_output = convert_json_to_text_format(json_data)
        
        # Apply the replacement function
        fib_output = replace_german_sharp_s(fib_output)
        ic_output = replace_german_sharp_s(ic_output)

        return f"{ic_output}\n---\n{fib_output}"
    except json.JSONDecodeError as e:

        st.error(f"Fehler beim Parsen von JSON: {e}")
        st.text("Bereinigte Eingabe:")
        st.code(cleaned_json_string, language='json')
        st.text("Originale Eingabe:")
        st.code(json_string)
        
        try:
            if not cleaned_json_string.strip().endswith(']'):
                cleaned_json_string += ']'
            partial_json = json.loads(cleaned_json_string)
            st.warning("Teilweises JSON konnte gerettet werden. Ergebnisse können unvollständig sein.")
            fib_output, ic_output = convert_json_to_text_format(partial_json)
            return f"{ic_output}\n---\n{fib_output}"
        except:
            st.error("Teilweises JSON konnte nicht gerettet werden.")
            return "Fehler: Ungültiges JSON-Format"
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung der Eingabe: {str(e)}")
        st.text("Originale Eingabe:")
        st.code(json_string)
        return "Fehler: Eingabe konnte nicht verarbeitet werden"

def get_chatgpt_response(prompt, model, image=None, selected_language="English"):
    """Fetches a response from OpenAI GPT with error handling."""
    if not client:
        st.error("Kein gültiger OpenAI-API-Schlüssel vorhanden. Bitte geben Sie Ihren API-Schlüssel ein.")
        return None

    try:
        # System Prompt with language instructions
        system_prompt = (
            """
            Du bist ein Experte im Bildungsbereich, spezialisiert auf die Erstellung von Testfragen und -antworten zu allen Themen, unter Einhaltung der Bloom's Taxonomy. Deine Aufgabe ist es, hochwertige Frage-Antwort-Sets basierend auf dem vom Benutzer bereitgestellten Material zu erstellen, wobei jede Frage einer spezifischen Ebene der Bloom's Taxonomy entspricht: Erinnern, Verstehen, Anwenden, Analysieren, Bewerten und Erstellen.

            Der Benutzer wird entweder Text oder ein Bild hochladen. Deine Aufgaben sind wie folgt:

            **Input-Analyse:**

            - Du analysierst den Inhalt sorgfältig, um die Schlüsselkonzepte und wichtigen Informationen zu verstehen.
            - Falls vorhanden, du achtest auf Diagramme, Grafiken, Bilder oder Infografiken, um Bildungsinhalte abzuleiten.

            **Fragen-Generierung nach Bloom-Ebene:**
            Basierend auf dem analysierten Material generierst du Fragen über alle die folgenden Ebenen der Bloom's Taxonomy:

            - **Erinnern**: Einfache, abrufbasierte Fragen.
            - **Verstehen**: Fragen, die das Verständnis des Materials bewerten.
            - **Anwenden**: Fragen, die die Anwendung des Wissens in praktischen Situationen erfordern.
            """
        )
        
        if image:
            base64_image = process_image(image)
            # Embed the image using Markdown syntax
            prompt_with_image = f"{prompt}\n\n![Image](data:image/jpeg;base64,{base64_image})"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_with_image}
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=15000,  # Adjusted max tokens
            temperature=0.6
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Fehler bei der Kommunikation mit der OpenAI API: {e}")
        logging.error(f"Fehler bei der Kommunikation mit der OpenAI API: {e}")
        return None

def generate_questions(user_input, learning_goals, selected_types, content, is_image, file_name, selected_language, selected_model, generated_content):
    """Generates questions for the given content (text or image) and appends them to the generated_content dictionary."""
    if not client:
        st.error("Ein gültiger OpenAI-API-Schlüssel ist erforderlich, um Fragen zu generieren.")
        return

    for msg_type in selected_types:
        prompt_template = read_prompt_from_md(msg_type)
        full_prompt = f"{prompt_template}\n\nBenutzereingabe: {user_input}\n\nLernziele: {learning_goals}"
        try:
            response = get_chatgpt_response(full_prompt, model=selected_model, image=content if is_image else None, selected_language=selected_language)
            if response:
                if msg_type == "inline_fib":
                    processed_response = transform_output(response)
                    key = f"Fragen für {file_name} - Inline/FIB"
                else:
                    key = f"Fragen für {file_name} - {msg_type.replace('_', ' ').title()}"
                    processed_response = response

                if key not in generated_content:
                    generated_content[key] = ""

                generated_content[key] += f"{processed_response}\n\n"
            else:
                st.error(f"Fehler bei der Generierung einer Antwort für {msg_type} in Datei {file_name}.")
        except Exception as e:
            st.error(f"Ein Fehler ist für {msg_type} in Datei {file_name} aufgetreten: {str(e)}")

@st.cache_data
def convert_pdf_to_images(file):
    """Converts PDF pages to images."""
    images = convert_from_bytes(file.read())
    return images

@st.cache_data
def extract_text_from_pdf(file):
    """Extracts text from PDF using PyPDF2."""
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text.strip()

@st.cache_data
def extract_text_from_docx(file):
    """Extracts text from DOCX file."""
    doc = docx.Document(file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text.strip()

def is_pdf_ocr(text):
    """Checks if the PDF contains OCR text (implementation required)."""
    # Dummy implementation; adjust as needed
    return bool(text)

def process_pdf(file):
    text_content = extract_text_from_pdf(file)
    
    # If no text is found, assume it's a non-OCR PDF
    if not text_content or not is_pdf_ocr(text_content):
        st.warning(f"PDF '{file.name}' ist möglicherweise nicht OCR-geschützt. Textextraktion fehlgeschlagen. Bitte laden Sie ein OCR-PDF hoch.")
        images = convert_pdf_to_images(file)
        return None, images
    else:
        return text_content, None

def main():
    """Main function for the Streamlit app."""
    # Model selection with dropdown
    st.subheader("Modell für die Generierung auswählen:")
    model_options = ["gpt-4o", "gpt-4o-mini"]
    selected_model = st.selectbox("Wählen Sie das Modell aus:", model_options, index=0)

    # Language selection with radio buttons
    st.subheader("Sprache für generierte Fragen auswählen:")
    languages = {
        "Deutsch": "German",
        "Englisch": "English",
        "Französisch": "French",
        "Italienisch": "Italian",
        "Spanisch": "Spanish"
    }
    selected_language = st.radio("Wählen Sie die Sprache für die Ausgabe:", list(languages.keys()), index=0)

    # File uploader section
    uploaded_files = st.file_uploader(
        "Laden Sie eine oder mehrere PDF, DOCX oder Bilddateien hoch", 
        type=["pdf", "docx", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.cache_data.clear()  # Clear cache to avoid stale data

    # Categorize uploaded files
    images = [f for f in uploaded_files if f.type.startswith('image/')]
    pdfs = [f for f in uploaded_files if f.type == 'application/pdf']
    docx_files = [f for f in uploaded_files if f.type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']

    generated_content = {}

    # Processing DOCX files
    if docx_files:
        st.header("Verarbeitete DOCX-Dateien")
        for docx_file in docx_files:
            text_content = extract_text_from_docx(docx_file)
            st.markdown(f"### {docx_file.name}")
            st.text_area(f"Extrahierter Text aus {docx_file.name}:", value=text_content, height=200, key=f"docx_{docx_file.name}")

    # Processing PDF files
    if pdfs:
        st.header("Verarbeitete PDFs")
        for pdf in pdfs:
            text_content, images_from_pdf = process_pdf(pdf)
            st.markdown(f"### {pdf.name}")
            if text_content:
                st.text_area(f"Extrahierter Text aus {pdf.name}:", value=text_content, height=200, key=f"pdf_text_{pdf.name}")
            if images_from_pdf:
                st.image(images_from_pdf, caption=f'PDF Seiten aus {pdf.name}', use_column_width=True)

    # Processing Image files
    if images:
        st.header("Hochgeladene Bilder")
        for img in images:
            st.image(img, caption=img.name, use_column_width=True)

    # Custom CSS for Callouts
    st.markdown(
        """
        <style>
        .custom-info {
            background-color: #e7f3fe;
            padding: 10px;
            border-radius: 5px;
            border-left: 6px solid #2196F3;
        }
        .custom-success {
            background-color: #d4edda;
            padding: 10px;
            border-radius: 5px;
            border-left: 6px solid #28a745;
        }
        .custom-warning {
            background-color: #fff3cd;
            padding: 10px;
            border-radius: 5px;
            border-left: 6px solid #ffc107;
        }
        </style>
        """, unsafe_allow_html=True
    )

    # User Inputs for Images
    if images:
        st.subheader("Einstellungen für alle Bilder")
        image_user_input = st.text_area("Geben Sie Ihre Frage oder Anweisungen für die Bilder ein:", key="global_image_text_area")
        image_learning_goals = st.text_area("Lernziele für die Bilder (Optional):", key="global_image_learning_goals")
        image_selected_types = st.multiselect("Wählen Sie die Fragetypen zur Generierung für die Bilder aus:", MESSAGE_TYPES, key="global_image_selected_types")

        if st.button("Fragen für alle Bilder generieren"):
            if not client:
                st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein, um Fragen zu generieren.")
            elif image_user_input and image_selected_types:
                # Initialize generated_content for each image and question type
                for img in images:
                    for msg_type in image_selected_types:
                        if msg_type == "inline_fib":
                            key = f"Fragen für {img.name} - Inline/FIB"
                        else:
                            key = f"Fragen für {img.name} - {msg_type.replace('_', ' ').title()}"
                        generated_content[key] = ""

                # Generate questions for each image
                for img in images:
                    generate_questions(
                        user_input=image_user_input,
                        learning_goals=image_learning_goals,
                        selected_types=image_selected_types,
                        content=img,
                        is_image=True,
                        file_name=img.name,
                        selected_language=selected_language,
                        selected_model=selected_model,
                        generated_content=generated_content
                    )
                st.success("Fragen für alle Bilder wurden erfolgreich generiert.")
            else:
                st.warning("Bitte geben Sie Text ein und wählen Sie Fragetypen für die Bilder aus.")

    # User Inputs for PDFs
    if pdfs:
        st.subheader("Einstellungen für alle PDFs")
        pdf_user_input = st.text_area("Geben Sie Ihre Frage oder Anweisungen für die PDFs ein:", key="global_pdf_text_area")
        pdf_learning_goals = st.text_area("Lernziele für die PDFs (Optional):", key="global_pdf_learning_goals")
        pdf_selected_types = st.multiselect("Wählen Sie die Fragetypen zur Generierung für die PDFs aus:", MESSAGE_TYPES, key="global_pdf_selected_types")

        if st.button("Fragen für alle PDFs generieren"):
            if not client:
                st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein, um Fragen zu generieren.")
            elif pdf_user_input and pdf_selected_types:
                # Initialize generated_content for each PDF and question type
                for pdf in pdfs:
                    for msg_type in pdf_selected_types:
                        if msg_type == "inline_fib":
                            key = f"Fragen für {pdf.name} - Inline/FIB"
                        else:
                            key = f"Fragen für {pdf.name} - {msg_type.replace('_', ' ').title()}"
                        generated_content[key] = ""

                # Generate questions for each PDF
                for pdf in pdfs:
                    text_content, images_from_pdf = process_pdf(pdf)
                    if text_content:
                        generate_questions(
                            user_input=pdf_user_input,
                            learning_goals=pdf_learning_goals,
                            selected_types=pdf_selected_types,
                            content=text_content,
                            is_image=False,
                            file_name=pdf.name,
                            selected_language=selected_language,
                            selected_model=selected_model,
                            generated_content=generated_content
                        )
                    if images_from_pdf:
                        for idx, img in enumerate(images_from_pdf):
                            img_key = f"{pdf.name}_page_{idx+1}"
                            generate_questions(
                                user_input=pdf_user_input,
                                learning_goals=pdf_learning_goals,
                                selected_types=pdf_selected_types,
                                content=img,
                                is_image=True,
                                file_name=img_key,
                                selected_language=selected_language,
                                selected_model=selected_model,
                                generated_content=generated_content
                            )
                st.success("Fragen für alle PDFs wurden erfolgreich generiert.")
            else:
                st.warning("Bitte geben Sie Text ein und wählen Sie Fragetypen für die PDFs aus.")

    # Display and Download Generated Content
    if generated_content:
        st.header("Generierter Inhalt")
        for title, content in generated_content.items():
            st.subheader(title)
            st.text_area(title, value=content, height=300)

            # Download Button for Each Generated File
            b64 = base64.b64encode(content.encode()).decode()  # B64 encode
            href = f'<a href="data:text/plain;base64,{b64}" download="{title.replace(" ", "_")}.txt">📥 Download</a>'
            st.markdown(href, unsafe_allow_html=True)

        # Optional: Download All Contents as a ZIP File
        with tempfile.TemporaryDirectory() as tmpdirname:
            zip_path = os.path.join(tmpdirname, "generierte_antworten.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for title, content in generated_content.items():
                    filename = f"{title.replace(' ', '_')}.txt"
                    zipf.writestr(filename, content)
            with open(zip_path, 'rb') as f:
                zip_bytes = f.read()
            st.download_button(
                label="📥 Alle Antworten als ZIP herunterladen",
                data=zip_bytes,
                file_name="generierte_antworten.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    main()
