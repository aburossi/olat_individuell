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

# Logging für bessere Fehlerverfolgung einrichten
logging.basicConfig(level=logging.INFO)

# Seitenkonfiguration festlegen und Light Mode erzwingen (Optional)
st.set_page_config(
    page_title="📝 OLAT Fragen Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Optional: Enforce Light Mode using CSS (can be removed if not necessary)
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
    2. **Laden Sie eine oder mehrere PDF, DOCX oder Bilddateien hoch oder geben Sie Text direkt ein**: Wählen Sie eine oder mehrere Dateien von Ihrem Computer aus oder nutzen Sie das Textfeld unten.
    3. **Modell auswählen**: Wählen Sie das gewünschte Modell für die Generierung aus.
    4. **Sprache auswählen**: Wählen Sie die gewünschte Sprache für die generierten Fragen.
    5. **Fragetypen auswählen**: Wählen Sie die Typen der Fragen, die Sie generieren möchten.
    6. **Fragen generieren**: Klicken Sie auf die Schaltfläche "Fragen generieren", um den Prozess zu starten.
    7. **Generierte Inhalte herunterladen**: Nach der Generierung können Sie die Antworten herunterladen.
    """)
    
    # Kosteninformationen und Frage-Erklärungen
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

# Liste der verfügbaren Fragetypen (global)
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
    try:
        with open(f"{filename}.md", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Die Prompt-Datei '{filename}.md' wurde nicht gefunden.")
        return ""

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
    """Ruft eine Antwort von OpenAI GPT mit Fehlerbehandlung ab."""
    if not client:
        st.error("Kein gültiger OpenAI-API-Schlüssel vorhanden. Bitte geben Sie Ihren API-Schlüssel ein.")
        return None

    try:
        # System-Prompt erstellen, der Sprachinstruktionen enthält
        system_prompt = (
            """
            Du bist ein Experte im Bildungsbereich, spezialisiert auf die Erstellung von Testfragen und -antworten zu allen Themen, unter Einhaltung der Bloom's Taxonomy. Deine Aufgabe ist es, hochwertige Frage-Antwort-Sets basierend auf dem vom Benutzer bereitgestellten Material zu erstellen, wobei jede Frage einer spezifischen Ebene der Bloom's Taxonomy entspricht: Erinnern, Verstehen, Anwenden, Analysieren, Bewerten und Erstellen.

            Der Benutzer wird entweder Text oder ein Bild hochladen. Deine Aufgaben sind wie folgt:

            **Input-Analyse:**

            - Du analysierst den Inhalt sorgfältig, um die Schlüsselkonzepte und wichtigen Informationen zu verstehen.
            - Falls vorhanden, achtest du auf Diagramme, Grafiken, Bilder oder Infografiken, um Bildungsinhalte abzuleiten.

            **Fragen-Generierung nach Bloom-Ebene:**
            Basierend auf dem analysierten Material generierst du Fragen über alle die folgenden Ebenen der Bloom's Taxonomy:

            - **Erinnern**: Einfache, abrufbasierte Fragen.
            - **Verstehen**: Fragen, die das Verständnis des Materials bewerten.
            - **Anwenden**: Fragen, die die Anwendung des Wissens in praktischen Situationen erfordern.
            - **Analysieren**: Fragen, die die Fähigkeit zur Analyse des Materials testen.
            - **Bewerten**: Fragen, die die Bewertung von Informationen oder Ideen verlangen.
            - **Erstellen**: Fragen, die die Erstellung neuer Inhalte oder Konzepte erfordern.
            """
        )
        
        if image:
            base64_image = process_image(image)
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
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
                {"role": "user", "content": prompt}
            ]

        response = client.chat.completions.create(
            model=model,  # Dynamische Modellwahl
            messages=messages,
            max_tokens=15000,  # Erhöht auf 15000
            temperature=0.6
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Fehler bei der Kommunikation mit der OpenAI API: {e}")
        logging.error(f"Fehler bei der Kommunikation mit der OpenAI API: {e}")
        return None

@st.cache_data
def convert_pdf_to_images(file):
    """Konvertiert PDF-Seiten in Bilder."""
    images = convert_from_bytes(file.read())
    return images

@st.cache_data
def extract_text_from_pdf(file):
    """Extrahiert Text aus PDF mit PyPDF2."""
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text.strip()

@st.cache_data
def extract_text_from_docx(file):
    """Extrahiert Text aus DOCX-Datei."""
    doc = docx.Document(file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text.strip()

def is_pdf_ocr(text):
    """Prüft, ob das PDF OCR-Text enthält (Implementierung erforderlich)."""
    # Dummy-Implementierung, bitte nach Bedarf anpassen
    return bool(text)

def process_pdf(file):
    text_content = extract_text_from_pdf(file)
    
    # Wenn kein Text gefunden wurde, nehme an, dass es ein nicht-OCR-PDF ist
    if not text_content or not is_pdf_ocr(text_content):
        st.warning("Dieses PDF ist nicht OCR-geschützt. Textextraktion fehlgeschlagen. Bitte laden Sie ein OCR-PDF hoch.")
        images = convert_pdf_to_images(file)
        return None, images  # Fallback zur Bildverarbeitung
    else:
        return text_content, None

def generate_questions_for_content(text, user_input, learning_goals, selected_types, selected_language, selected_model, image=None):
    """Generiert Fragen basierend auf dem bereitgestellten Inhalt oder Bild."""
    all_responses = ""
    generated_content = {}
    for msg_type in selected_types:
        prompt_template = read_prompt_from_md(msg_type)
        if not prompt_template:
            continue  # Überspringen, wenn keine Prompt-Datei gefunden wurde

        # Kombination des Prompt-Templates mit Benutzerinput und Lernzielen
        full_prompt = f"{prompt_template}\n\nBenutzereingabe: {user_input}\n\nLernziele: {learning_goals}"
        
        response = get_chatgpt_response(full_prompt, model=selected_model, image=image, selected_language=selected_language)
        
        if response:
            if msg_type == "inline_fib":
                processed_response = transform_output(response)
                generated_content[f"{msg_type.replace('_', ' ').title()} (Verarbeitet)"] = processed_response
                all_responses += f"{processed_response}\n\n"
            else:
                generated_content[msg_type.replace('_', ' ').title()] = response
                all_responses += f"{response}\n\n"
        else:
            st.error(f"Fehler bei der Generierung einer Antwort für {msg_type}.")

    # Reinigungsfunktion auf alle Antworten anwenden
    all_responses = replace_german_sharp_s(all_responses)

    return all_responses

def generate_all_questions(uploaded_files, general_user_input, general_learning_goals, selected_types, selected_language, selected_model):
    """Generiert Fragen für alle hochgeladenen Dateien und gibt eine ZIP-Datei zurück."""
    if not client:
        st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein, um Fragen zu generieren.")
        return None

    if not selected_types:
        st.error("Bitte wählen Sie mindestens einen Fragetyp aus.")
        return None

    # In-Memory ZIP-Datei erstellen
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for uploaded_file in uploaded_files:
            filename = uploaded_file.name
            st.info(f"Generiere Fragen für '{filename}'...")
            
            if uploaded_file.type == "application/pdf":
                text_content, images = process_pdf(uploaded_file)
                if text_content:
                    # Generieren der Fragen basierend auf dem extrahierten Text
                    questions_text = generate_questions_for_content(
                        text=text_content,
                        user_input=general_user_input,
                        learning_goals=general_learning_goals,
                        selected_types=selected_types,
                        selected_language=selected_language,
                        selected_model=selected_model
                    )
                elif images:
                    # Wenn PDF als Bilder verarbeitet wird, generiere Fragen für jede Seite
                    questions_text = ""
                    for idx, image in enumerate(images):
                        page_number = idx + 1
                        st.info(f"Generiere Fragen für Seite {page_number} von '{filename}'...")
                        questions = generate_questions_for_content(
                            text="",
                            user_input=general_user_input,
                            learning_goals=general_learning_goals,
                            selected_types=selected_types,
                            selected_language=selected_language,
                            selected_model=selected_model,
                            image=image
                        )
                        questions_text += f"### Seite {page_number}\n{questions}\n\n"
                else:
                    st.error(f"Fehler beim Verarbeiten von '{filename}'.")
                    continue
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text_content = extract_text_from_docx(uploaded_file)
                questions_text = generate_questions_for_content(
                    text=text_content,
                    user_input=general_user_input,
                    learning_goals=general_learning_goals,
                    selected_types=selected_types,
                    selected_language=selected_language,
                    selected_model=selected_model
                )
            elif uploaded_file.type.startswith('image/'):
                image_content = Image.open(uploaded_file)
                questions_text = generate_questions_for_content(
                    text="",
                    user_input=general_user_input,
                    learning_goals=general_learning_goals,
                    selected_types=selected_types,
                    selected_language=selected_language,
                    selected_model=selected_model,
                    image=image_content
                )
            else:
                st.error(f"Nicht unterstützter Dateityp für '{filename}'.")
                continue

            # Speichern der generierten Fragen als Textdatei im ZIP
            txt_filename = f"{os.path.splitext(filename)[0]}_olat.txt"
            zip_file.writestr(txt_filename, questions_text)
            st.success(f"Fragen für '{filename}' generiert und hinzugefügt.")

    zip_buffer.seek(0)
    return zip_buffer

def generate_questions_with_image(user_input, learning_goals, selected_types, image, selected_language, selected_model):
    """Generiert Fragen für das Bild und behandelt Fehler."""
    if not client:
        st.error("Ein gültiger OpenAI-API-Schlüssel ist erforderlich, um Fragen zu generieren.")
        return

    all_responses = ""
    generated_content = {}
    for msg_type in selected_types:
        prompt_template = read_prompt_from_md(msg_type)
        if not prompt_template:
            continue  # Überspringen, wenn keine Prompt-Datei gefunden wurde

        full_prompt = f"{prompt_template}\n\nBenutzereingabe: {user_input}\n\nLernziele: {learning_goals}"
        try:
            response = get_chatgpt_response(
                prompt=full_prompt,
                model=selected_model,
                image=image,
                selected_language=selected_language
            )
            if response:
                if msg_type == "inline_fib":
                    processed_response = transform_output(response)
                    generated_content[f"{msg_type.replace('_', ' ').title()} (Verarbeitet)"] = processed_response
                    all_responses += f"{processed_response}\n\n"
                else:
                    generated_content[msg_type.replace('_', ' ').title()] = response
                    all_responses += f"{response}\n\n"
            else:
                st.error(f"Fehler bei der Generierung einer Antwort für {msg_type}.")
        except Exception as e:
            st.error(f"Ein Fehler ist für {msg_type} aufgetreten: {str(e)}")
    
    # Reinigungsfunktion auf alle Antworten anwenden
    all_responses = replace_german_sharp_s(all_responses)

    # Generierten Inhalt mit Häkchen anzeigen
    st.subheader("Generierter Inhalt:")
    for title in generated_content.keys():
        st.write(f"✔ {title}")

    # Download-Button für alle Antworten
    if all_responses:
        st.download_button(
            label="Alle Antworten herunterladen",
            data=all_responses,
            file_name="alle_antworten.txt",
            mime="text/plain"
        )

def main():
    """Hauptfunktion für die Streamlit-App."""
    # Modellenauswahl mit Checkbox
    st.subheader("Modell für die Generierung auswählen:")
    model_options = ["gpt-4o", "gpt-4o-mini"]
    selected_model = st.selectbox(
        "Wählen Sie das Modell aus:",
        model_options,
        index=0
    )
    
    # Sprachenauswahl mit Radiobuttons
    st.subheader("Sprache für generierte Fragen auswählen:")
    languages = {
        "Deutsch": "German",
        "Englisch": "English",
        "Französisch": "French",
        "Italienisch": "Italian",
        "Spanisch": "Spanish"
    }
    selected_language = st.radio("Wählen Sie die Sprache für die Ausgabe:", list(languages.keys()), index=0)

    # Dateiuploader-Bereich mit Mehrfachauswahl
    uploaded_files = st.file_uploader(
        "Laden Sie eine oder mehrere PDF, DOCX oder Bilddateien hoch", 
        type=["pdf", "docx", "jpg", "jpeg", "png"], 
        accept_multiple_files=True
    )
    
    # Direktes Texteingabefeld
    st.subheader("Oder geben Sie Ihren Text direkt ein:")
    direct_text = st.text_area("Direkte Texteingabe:", height=200)

    # Zusammenführen von Benutzerinput und Dateien
    has_uploaded_files = len(uploaded_files) > 0
    has_direct_text = direct_text.strip() != ""

    if has_uploaded_files:
        st.markdown("### 📂 Hochgeladene Dateien")
        for idx, uploaded_file in enumerate(uploaded_files):
            file_idx = idx + 1
            with st.expander(f"📄 Datei {file_idx}: {uploaded_file.name}", expanded=False):
                if uploaded_file.type == "application/pdf":
                    text_content, images = process_pdf(uploaded_file)
                    if text_content:
                        st.text_area("Extrahierter Text:", value=text_content, height=200, disabled=True)
                    elif images:
                        for img_idx, image in enumerate(images):
                            st.image(image, caption=f'Seite {img_idx+1}', use_column_width=True)
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    text_content = extract_text_from_docx(uploaded_file)
                    st.text_area("Extrahierter Text:", value=text_content, height=200, disabled=True)
                elif uploaded_file.type.startswith('image/'):
                    image_content = Image.open(uploaded_file)
                    st.image(image_content, caption=f'Hochgeladenes Bild {file_idx}: {uploaded_file.name}', use_column_width=True)
                else:
                    st.error(f"Nicht unterstützter Dateityp für '{uploaded_file.name}'. Bitte laden Sie eine PDF, DOCX oder Bilddatei hoch.")

    if has_direct_text:
        with st.expander("📄 Direkte Texteingabe Vorschau", expanded=False):
            st.write(direct_text)

    # Benutzerdefiniertes CSS für hellblauen Hintergrund in Info-Callouts
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

    # Eingabefelder für Lernziele
    st.subheader("Lernziele auswählen:")
    learning_goals = st.text_area("Lernziele (Optional):")

    # Fragetypen auswählen
    st.subheader("Fragetypen auswählen:")
    selected_types = st.multiselect("Wählen Sie die Fragetypen zur Generierung aus:", MESSAGE_TYPES)

    # Button zum Generieren von Fragen
    if st.button("Fragen generieren"):
        if not client:
            st.error("Bitte geben Sie Ihren OpenAI-API-Schlüssel ein, um Fragen zu generieren.")
        elif not (has_uploaded_files or has_direct_text):
            st.warning("Bitte geben Sie Text ein oder laden Sie eine Datei hoch.")
        elif not selected_types:
            st.warning("Bitte wählen Sie mindestens einen Fragetyp aus.")
        else:
            with st.spinner("Generiere Fragen..."):
                if has_direct_text and not has_uploaded_files:
                    # Nur direkter Text eingegeben
                    questions_text = generate_questions_for_content(
                        text=direct_text,
                        user_input=direct_text,
                        learning_goals=learning_goals,
                        selected_types=selected_types,
                        selected_language=selected_language,
                        selected_model=selected_model
                    )
                    # Anzeigen der generierten Fragen
                    st.subheader("Generierter Inhalt:")
                    st.write(questions_text)
                    # Download-Button
                    st.download_button(
                        label="Generierte Fragen herunterladen",
                        data=questions_text,
                        file_name="direct_input_olat.txt",
                        mime="text/plain"
                    )
                elif has_uploaded_files and not has_direct_text:
                    # Nur Dateien hochgeladen
                    zip_buffer = generate_all_questions(
                        uploaded_files=uploaded_files,
                        general_user_input="",  # Kann angepasst werden, wenn nötig
                        general_learning_goals=learning_goals,
                        selected_types=selected_types,
                        selected_language=selected_language,
                        selected_model=selected_model
                    )
                    if zip_buffer:
                        if len(uploaded_files) > 1:
                            st.success("Fragen erfolgreich generiert!")
                            st.download_button(
                                label="🗜️ Generierte Fragen als ZIP herunterladen",
                                data=zip_buffer,
                                file_name="generierte_fragen.zip",
                                mime="application/zip"
                            )
                        else:
                            # Einzelne Datei: Download der einzelnen Textdatei
                            with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                                for file in zip_ref.namelist():
                                    extracted_file = zip_ref.read(file)
                                    st.success("Fragen erfolgreich generiert!")
                                    st.download_button(
                                        label="📝 Generierte Fragen herunterladen",
                                        data=extracted_file,
                                        file_name=file,
                                        mime="text/plain"
                                    )
                elif has_uploaded_files and has_direct_text:
                    # Sowohl Text eingegeben als auch Dateien hochgeladen
                    # Generiere Fragen für Text
                    questions_text = generate_questions_for_content(
                        text=direct_text,
                        user_input=direct_text,
                        learning_goals=learning_goals,
                        selected_types=selected_types,
                        selected_language=selected_language,
                        selected_model=selected_model
                    )
                    # Generiere Fragen für Dateien und packe in ZIP
                    zip_buffer = generate_all_questions(
                        uploaded_files=uploaded_files,
                        general_user_input="",  # Kann angepasst werden, wenn nötig
                        general_learning_goals=learning_goals,
                        selected_types=selected_types,
                        selected_language=selected_language,
                        selected_model=selected_model
                    )
                    # Speichern der direkten Texteingabe in der ZIP
                    if zip_buffer:
                        with zipfile.ZipFile(zip_buffer, "a") as zip_file:
                            zip_file.writestr("direct_input_olat.txt", questions_text)
                        zip_buffer.seek(0)
                        st.success("Fragen erfolgreich generiert!")
                        st.download_button(
                            label="🗜️ Generierte Fragen als ZIP herunterladen",
                            data=zip_buffer,
                            file_name="generierte_fragen.zip",
                            mime="application/zip"
                        )

    # Funktion zur Verarbeitung von Bildern innerhalb von PDFs
    def process_images(images, selected_language, selected_model):
        """Verarbeitet hochgeladene Bilder und generiert Fragen."""
        for idx, image in enumerate(images):
            with st.expander(f"📸 Bild {idx+1}", expanded=False):
                st.image(image, caption=f'Seite {idx+1}', use_column_width=True)

                # Textbereich für Benutzereingaben und Lernziele
                user_input = st.text_area(f"Geben Sie Ihre Frage oder Anweisungen für Seite {idx+1} ein:", key=f"text_area_{idx}")
                learning_goals_page = st.text_area(f"Lernziele für Seite {idx+1} (Optional):", key=f"learning_goals_{idx}")

                # Fragetypen auswählen
                selected_types_page = st.multiselect(f"Wählen Sie die Fragetypen für Seite {idx+1} aus:", MESSAGE_TYPES, key=f"selected_types_{idx}")

                # Button zum Generieren von Fragen für die Seite
                if st.button(f"Fragen für Seite {idx+1} generieren", key=f"generate_button_{idx}"):
                    # Fragen nur generieren, wenn Benutzereingaben und ausgewählte Fragetypen vorhanden sind
                    if user_input and selected_types_page:
                        generate_questions_with_image(
                            user_input=user_input,
                            learning_goals=learning_goals_page,
                            selected_types=selected_types_page,
                            image=image,
                            selected_language=selected_language,
                            selected_model=selected_model
                        )
                    else:
                        st.warning(f"Bitte geben Sie Text ein und wählen Sie Fragetypen für Seite {idx+1} aus.")

if __name__ == "__main__":
    main()
