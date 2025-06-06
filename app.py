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
import hashlib # Added for caching

# Logging für bessere Fehlerverfolgung einrichten
logging.basicConfig(level=logging.INFO)

# Seitenkonfiguration festlegen und Light Mode erzwingen
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

# Titel der App
st.title("📝 Fragen Generator")

# Seitenleiste für Anweisungen und Zusatzinformationen
with st.sidebar:
    st.header("❗ **So verwenden Sie diese App**")
    
    st.markdown("""
    1. **Geben Sie Ihren OpenAI-API-Schlüssel ein**: Erhalten Sie Ihren API-Schlüssel von [OpenAI](https://platform.openai.com/account/api-keys) und geben Sie ihn im Feld *OpenAI-API-Schlüssel* ein.
    """)
    
    # YouTube-Video in die Seitenleiste einbetten
    components.html("""
        <iframe width="100%" height="180" src="https://www.youtube.com/embed/NsTAjBdHb1k" 
        title="Demo-Video auf Deutsch" frameborder="0" allow="accelerometer; autoplay; 
        clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
        </iframe>
    """, height=180)
    
    # Weitere Anweisungen
    st.markdown("""
    2. **Laden Sie eine PDF, DOCX oder Bilddatei hoch**: Wählen Sie eine Datei von Ihrem Computer aus.
    3. **Sprache auswählen**: Wählen Sie die gewünschte Sprache für die generierten Fragen.
    4. **Fragetypen auswählen**: Wählen Sie die Typen der Fragen, die Sie generieren möchten.
    5. **Fragen generieren**: Klicken Sie auf die Schaltfläche "Fragen generieren", um den Prozess zu starten.
    6. **Generierte Inhalte herunterladen**: Nach der Generierung können Sie die Antworten herunterladen.
    """)
    
    # Kosteninformationen und Frage-Erklärungen
    st.markdown('''
    <div class="custom-info">
        <strong>ℹ️ Kosten- und Cache-Informationen:</strong>
        <ul>
            <li>Nutzungskosten hängen von der <strong>Länge der Eingabe</strong> ab (0,01 $ - 0,1 $).</li>
            <li>Jeder Fragetyp kostet ca. 0,01 $.</li>
            <li><strong>Caching ist aktiv</strong>: Fragen für denselben Text werden nur einmal generiert. Ändern Sie den Text, um neue Fragen zu erhalten.</li>
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

    # Trennlinie und Lizenzinformationen
    st.markdown("---")
    st.header("📜 Lizenz")
    st.markdown("""
    Diese Anwendung steht unter der [MIT-Lizenz](https://opensource.org/licenses/MIT). 
    Sie dürfen diese Software verwenden, ändern und weitergeben, solange die ursprüngliche Lizenz beibehalten wird.
    """)

    # Kontaktinformationen
    st.header("💬 Kontakt")
    st.markdown("""
    Für Unterstützung, Fragen oder um mehr über die Nutzung dieser App zu erfahren, kannst du gerne auf mich zukommen.
    **Kontakt**: [Pietro](mailto:pietro.rossi@bbw.ch)
    """)

# Streamlit Widgets für API-Schlüssel Eingabe
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

# Liste der verfügbaren Fragetypen
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
    """Liest den Prompt aus einer Markdown-Datei und speichert das Ergebnis zwischen."""
    # Construct the correct path to the markdown file inside the 'prompts' folder
    file_path = os.path.join("prompts", f"{filename}.md")
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def process_image(_image):
    """Verarbeitet und verkleinert ein Bild, um den Speicherverbrauch zu reduzieren."""
    if isinstance(_image, (str, bytes)):
        img = Image.open(io.BytesIO(base64.b64decode(_image) if isinstance(_image, str) else _image))
    elif isinstance(_image, Image.Image):
        img = _image
    else:
        img = Image.open(_image)

    # Konvertiere in RGB-Modus, falls erforderlich
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Verkleinern, wenn das Bild zu groß ist
    max_size = 1000  # Reduzierte Maximalgröße zur Verringerung des Speicherverbrauchs
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))

    # Speichern in Bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    return base64.b64encode(img_byte_arr).decode('utf-8')

def replace_german_sharp_s(text):
    """Ersetzt alle Vorkommen von 'ß' durch 'ss'."""
    return text.replace('ß', 'ss')


def clean_json_string(s):
    s = s.strip()
    # Remove markdown code block syntax
    s = re.sub(r'^```json\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'```\s*$', '', s)
    s = s.strip()
    # Standardize whitespace
    s = re.sub(r'\s+', ' ', s)
    # Escape newlines within JSON string values
    s = re.sub(r'(?<=text": ")(.+?)(?=")', lambda m: m.group(1).replace('\n', '\\n'), s)
    # Ensure it's valid characters
    s = ''.join(char for char in s if ord(char) >= 32 or char in ('\n', '\t', '\r'))
    # Extract the main JSON array/object
    match = re.search(r'\[.*\]', s, re.DOTALL)
    if not match:
        match = re.search(r'\{.*\}', s, re.DOTALL)
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

        # Use a temporary placeholder that is unlikely to appear in the text
        placeholder = "||BLANK||"
        original_text = text
        for blank in blanks:
            original_text = original_text.replace(blank, placeholder, 1)

        parts = original_text.split(placeholder)
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
        
        # Anwenden der Reinigungsfunktion
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
    """Ruft eine Antwort von OpenAI GPT ab und implementiert die Cache-Protokollierung."""
    if not client:
        st.error("Kein gültiger OpenAI-API-Schlüssel vorhanden. Bitte geben Sie Ihren API-Schlüssel ein.")
        return None

    try:
        # System-Prompt erstellen
        system_prompt = (
            """
            Du bist ein Experte im Bildungsbereich...
            [Your extensive system prompt remains here]
            """
        )
        
        if image:
            base64_image = process_image(image)
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": f"Generate questions in {selected_language}. {prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate questions in {selected_language}. {prompt}"}
            ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,  # Adjusted for modern models
            temperature=0.6
        )
        
        # --- START of OpenAI-Side Caching Logic ---
        if response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cache_info_str = ""
            
            prompt_details = getattr(response.usage, 'prompt_tokens_details', None)
            
            if prompt_details and isinstance(prompt_details, dict):
                cached_tokens = prompt_details.get('cached_tokens', 0)
                if cached_tokens and prompt_tokens > 0:
                    cache_percentage = (cached_tokens / prompt_tokens * 100)
                    cache_info_str = f" (Cached={cached_tokens}, {cache_percentage:.1f}%)"
                elif cached_tokens:
                    cache_info_str = f" (Cached={cached_tokens})"
            
            # Display token usage and cache info
            st.info(f"📊 Token Usage: Prompt={prompt_tokens}{cache_info_str}, Completion={completion_tokens}")
            logging.info(f"API Call Token Usage: Prompt={prompt_tokens}{cache_info_str}, Completion={completion_tokens}")
        else:
            st.warning("Token usage details not available in the API response.")
        # --- END of OpenAI-Side Caching Logic ---
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Fehler bei der Kommunikation mit der OpenAI API: {e}")
        logging.error(f"Fehler bei der Kommunikation mit der OpenAI API: {e}")
        return None


def process_images(images, selected_language, selected_model):
    """Verarbeitet hochgeladene Bilder und generiert Fragen mit Caching."""
    for idx, image in enumerate(images):
        st.image(image, caption=f'Seite {idx+1}', use_column_width=True)

        user_input = st.text_area(f"Geben Sie Ihre Frage oder Anweisungen für Seite {idx+1} ein:", key=f"text_area_{idx}")
        learning_goals = st.text_area(f"Lernziele für Seite {idx+1} (Optional):", key=f"learning_goals_{idx}")
        selected_types = st.multiselect(f"Wählen Sie die Fragetypen für Seite {idx+1} aus:", MESSAGE_TYPES, key=f"selected_types_{idx}")

        if st.button(f"Fragen für Seite {idx+1} generieren", key=f"generate_button_{idx}"):
            if user_input and selected_types:
                # Pass page index for unique caching
                generate_questions(user_input, learning_goals, selected_types, image, selected_language, selected_model, page_index=idx)
            else:
                st.warning(f"Bitte geben Sie Text ein und wählen Sie Fragetypen für Seite {idx+1} aus.")

def generate_questions(user_input, learning_goals, selected_types, image, selected_language, selected_model, page_index=None):
    """Generiert Fragen und implementiert Anwendungs-seitiges Caching."""
    if not client:
        st.error("Ein gültiger OpenAI-API-Schlüssel ist erforderlich, um Fragen zu generieren.")
        return

    # --- START of Application-Side Caching Logic ---
    # Create unique keys for session state based on page index
    cache_key = f"cached_responses_{page_index}" if page_index is not None else "cached_responses"
    hash_key = f"source_content_hash_{page_index}" if page_index is not None else "source_content_hash"
    
    # Initialize session state if it doesn't exist
    if cache_key not in st.session_state:
        st.session_state[cache_key] = {}
    if hash_key not in st.session_state:
        st.session_state[hash_key] = None
        
    # Create a hash of the current source content to detect changes
    content_to_hash = user_input + (process_image(image) if image else "")
    current_content_hash = hashlib.md5(content_to_hash.encode()).hexdigest()

    # If the source content has changed, clear the old cache for this specific context
    if st.session_state[hash_key] != current_content_hash:
        st.info("Quellinhalt hat sich geändert. Leere den bisherigen Cache.")
        st.session_state[cache_key] = {}
        st.session_state[hash_key] = current_content_hash
    # --- END of Application-Side Caching Logic ---
        
    all_responses = ""
    generated_content = {}
    
    with st.spinner("Generiere Fragen... dies kann einen Moment dauern."):
        for msg_type in selected_types:
            response = None
            # Check cache first
            if msg_type in st.session_state[cache_key]:
                st.success(f"💾 Antwort für '{msg_type.replace('_', ' ').title()}' aus dem Cache geladen.")
                response = st.session_state[cache_key][msg_type]
            else:
                st.info(f"🧠 Rufe OpenAI API für '{msg_type.replace('_', ' ').title()}' auf...")
                prompt_template = read_prompt_from_md(msg_type)
                full_prompt = f"{prompt_template}\n\nBenutzereingabe: {user_input}\n\nLernziele: {learning_goals}"
                try:
                    response = get_chatgpt_response(full_prompt, model=selected_model, image=image, selected_language=selected_language)
                    if response:
                        # Store successful response in cache
                        st.session_state[cache_key][msg_type] = response
                except Exception as e:
                    st.error(f"Ein Fehler ist für {msg_type} aufgetreten: {str(e)}")
            
            # Process the response (from cache or new)
            if response:
                if msg_type == "inline_fib":
                    processed_response = transform_output(response)
                    generated_content[f"{msg_type.replace('_', ' ').title()} (Verarbeitet)"] = processed_response
                    all_responses += f"{processed_response}\n\n"
                else:
                    cleaned_response = replace_german_sharp_s(response)
                    generated_content[msg_type.replace('_', ' ').title()] = cleaned_response
                    all_responses += f"{cleaned_response}\n\n"
            else:
                st.error(f"Fehler bei der Generierung einer Antwort für {msg_type}.")
    
    # Anzeigen des generierten Inhalts
    st.subheader("Generierter Inhalt:")
    for title in generated_content.keys():
        st.write(f"✔ {title}")

    if all_responses:
        st.download_button(
            label="Alle Antworten herunterladen",
            data=all_responses,
            file_name="alle_antworten.txt",
            mime="text/plain"
        )


@st.cache_data
def convert_pdf_to_images(file):
    """Konvertiert PDF-Seiten in Bilder."""
    return convert_from_bytes(file.read())

@st.cache_data
def extract_text_from_pdf(file):
    """Extrahiert Text aus PDF mit PyPDF2."""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
    text = "".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
    return text.strip()

@st.cache_data
def extract_text_from_docx(file):
    """Extrahiert Text aus DOCX-Datei."""
    doc = docx.Document(io.BytesIO(file.read()))
    return "\n".join([paragraph.text for paragraph in doc.paragraphs]).strip()

def process_pdf(file):
    file_bytes = file.getvalue()
    text_content = extract_text_from_pdf(io.BytesIO(file_bytes))
    
    if not text_content:
        st.warning("Kein Text im PDF gefunden. Es wird versucht, es als Bilder zu verarbeiten.")
        return None, convert_pdf_to_images(io.BytesIO(file_bytes))
    else:
        return text_content, None

def main():
    """Hauptfunktion für die Streamlit-App."""
    st.subheader("Modell für die Generierung auswählen:")
    model_options = ["gpt-4o", "gpt-4o-mini"]
    selected_model = st.selectbox("Wählen Sie das Modell aus:", model_options, index=0)

    st.subheader("Sprache für generierte Fragen auswählen:")
    languages = {
        "Deutsch": "German", "Englisch": "English", "Französisch": "French", 
        "Italienisch": "Italian", "Spanisch": "Spanish"
    }
    selected_language_key = st.radio("Wählen Sie die Sprache für die Ausgabe:", list(languages.keys()), index=0)
    selected_language = languages[selected_language_key]

    uploaded_file = st.file_uploader("Laden Sie eine PDF, DOCX oder Bilddatei hoch", type=["pdf", "docx", "jpg", "jpeg", "png"])

    text_content = ""
    image_content = None
    images = []

    if uploaded_file:
        # Clear Streamlit's function cache AND our session state cache
        if 'last_uploaded_filename' not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
            st.cache_data.clear()
            # Clear all potential session state caches
            for key in list(st.session_state.keys()):
                if key.startswith('cached_responses') or key.startswith('source_content_hash'):
                    del st.session_state[key]
            st.session_state.last_uploaded_filename = uploaded_file.name
            st.info("Neue Datei hochgeladen. Alle Caches wurden geleert.")

    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            text_content, images = process_pdf(uploaded_file)
            if text_content:
                st.success("Text aus PDF extrahiert. Sie können ihn nun bearbeiten.")
            elif images:
                st.success("PDF in Bilder konvertiert. Sie können jetzt Fragen zu jeder Seite stellen.")
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text_content = extract_text_from_docx(uploaded_file)
            st.success("Text erfolgreich extrahiert. Sie können ihn nun bearbeiten.")
        elif uploaded_file.type.startswith('image/'):
            image_content = Image.open(uploaded_file)
            st.image(image_content, caption='Hochgeladenes Bild', use_column_width=True)
            st.success("Bild erfolgreich hochgeladen.")

    if images:
        process_images(images, selected_language, selected_model)
    else:
        user_input = st.text_area("Geben Sie Ihren Text oder Ihre Frage zum Bild ein:", value=text_content, height=300)
        learning_goals = st.text_area("Lernziele (Optional):")
        
        selected_types = st.multiselect("Wählen Sie die Fragetypen zur Generierung aus:", MESSAGE_TYPES)
        
        # Custom CSS for callouts
        st.markdown(
            """
            <style>
            .custom-info { background-color: #e7f3fe; padding: 10px; border-radius: 5px; border-left: 6px solid #2196F3; }
            .custom-success { background-color: #d4edda; padding: 10px; border-radius: 5px; border-left: 6px solid #28a745; }
            .custom-warning { background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 6px solid #ffc107; }
            </style>
            """, unsafe_allow_html=True
        )
        
        if st.button("Fragen generieren"):
            if not client:
                st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein.")
            elif (user_input or image_content) and selected_types:
                generate_questions(user_input, learning_goals, selected_types, image_content, selected_language, selected_model)
            elif not user_input and not image_content:
                st.warning("Bitte geben Sie Text ein oder laden Sie eine Datei hoch.")
            elif not selected_types:
                st.warning("Bitte wählen Sie mindestens einen Fragetyp aus.")

if __name__ == "__main__":
    main()