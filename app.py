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
    2. **Laden Sie eine PDF, DOCX oder bis zu 10 Bilder hoch**: Wählen Sie eine oder mehrere Dateien von Ihrem Computer aus.
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

# NEW: Definition der Zielniveaus
ZIELNIVEAUS_MAP = {
    "A2 (elementar / Primarstufe, frühe Sek I)": "🟢 A2 (elementar / Primarstufe, frühe Sek I)\nVerwende einfache Satzstrukturen und grundlegenden Wortschatz. Die Fragen sollen sich auf vertraute Alltagssituationen beziehen. Verwende visuelle Hilfen, wenn möglich. Halte die Fragen kurz und klar. Vermeide abstrakte Begriffe.",
    "B1 (untere Sek II, Berufsschule, Realschule)": "🔵 B1 (untere Sek II, Berufsschule, Realschule)\nVerwende alltagsnahes, aber anspruchsvolleres Vokabular. Die Fragen sollen einfache Schlussfolgerungen und erste Transferleistungen ermöglichen. Verwende konkrete Kontexte (z. B. Schule, Arbeit, Freizeit). Halte sprachliche Komplexität moderat.",
    "B2 (obere Sek II, Maturität, Bachelorbeginn)": "🟡 B2 (obere Sek II, Maturität, Bachelorbeginn)\nVerwende akademisch orientierten Wortschatz und moderate sprachliche Komplexität. Die Fragen sollen analytisches und kritisches Denken fördern. Es sind auch hypothetische Szenarien erlaubt. Fremdwörter können vorkommen, aber sollten kontextuell erschließbar sein.",
    "C1 (Bachelor/Master, Hochschulreife)": "🟠 C1 (Bachelor/Master, Hochschulreife)\nVerwende komplexe Satzstrukturen und einen gehobenen, akademischen Sprachstil. Die Fragen sollen Argumentation, Bewertung und Synthese fördern. Die Lernenden sollen eigenständig Thesen entwickeln und verschiedene Perspektiven vergleichen können.",
    "C2 (Master/Expertenniveau)": "🔴 C2 (Master/Expertenniveau)\nVerwende präzise, abstrakte und komplexe Sprache. Die Fragen sollen kreative, originelle Denkprozesse anregen und fächerübergreifende Kompetenzen einbeziehen. Es wird ein hohes Maß an Autonomie und metakognitivem Denken vorausgesetzt."
}


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

def get_chatgpt_response(prompt, model, images=None, selected_language="English", reasoning_effort="medium", selected_zielniveau=""):
    """Ruft eine Antwort von OpenAI ab und implementiert die Cache-Protokollierung."""
    if not client:
        st.error("Kein gültiger OpenAI-API-Schlüssel vorhanden. Bitte geben Sie Ihren API-Schlüssel ein.")
        return None

    # System-Prompt, der für alle Modelle gilt
    system_prompt_template = (
        """
        Du bist ein Experte im Bildungsbereich, spezialisiert auf die Erstellung von Testfragen und -antworten zu allen Themen, unter Einhaltung der Bloom's Taxonomy. Deine Aufgabe ist es, hochwertige Frage-Antwort-Sets basierend auf dem vom Benutzer bereitgestellten Material zu erstellen, wobei jede Frage einer spezifischen Ebene der Bloom's Taxonomy entspricht: Erinnern, Verstehen, Anwenden, Analysieren, Bewerten und Erstellen.

        # Zielniveaus
        [ZIELNIVEAU_INJECTION]

        Der Benutzer wird entweder Text oder ein Bild hochladen. Deine Aufgaben sind wie folgt:

        **Input-Analyse:**

        - Du analysierst den Inhalt sorgfältig, um die Schlüsselkonzepte und wichtigen Informationen zu verstehen.
        - Falls vorhanden, achtest du auf Diagramme, Grafiken, Bilder oder Infografiken, um Bildungsinhalte abzuleiten.

        **Fragen-Generierung nach Bloom-Ebene und Zielniveau:**

        Basierend auf dem analysierten Material und dem angegebenen Zielniveau generierst du Fragen über alle die folgenden Ebenen der Bloom's Taxonomy. Achte darauf, dass die sprachliche Komplexität, der Umfang der Aufgabenstellung und die kognitiven Anforderungen dem Zielniveau angemessen sind:

        - **Erinnern**: Einfache, abrufbasierte Fragen.
        - **Verstehen**: Fragen, die das Verständnis des Materials bewerten.
        - **Anwenden**: Fragen, die die Anwendung des Wissens in praktischen Situationen erfordern.
        - **Analysieren**: Fragen, die das Zerlegen und Untersuchen von Konzepten und Zusammenhängen erfordern.
        - **Bewerten**: Fragen, die Urteilsbildung und begründete Meinungen verlangen.
        - **Erstellen**: Fragen, die kreative Synthese, neue Perspektiven oder eigene Lösungsansätze fördern.

        Achte stets darauf, dass die Formulierungen und kognitiven Anforderungen dem Niveau des vorgesehenen Lernendenkreises entsprechen.
        """
    )

    # Inject the selected Zielniveau into the prompt
    system_prompt = system_prompt_template.replace("[ZIELNIVEAU_INJECTION]", selected_zielniveau)

    try:
# ---- NEW: Logic for o4-mini Reasoning Model ----
        if model == "o4-mini":
            st.info(f"🧠 Rufe OpenAI Reasoning API (o4-mini) mit '{reasoning_effort}' Aufwand auf...")
            
            # Kombiniere System- und Benutzer-Prompt für das 'developer'-Feld
            full_text_prompt = f"{system_prompt}\n\nGenerate questions in {selected_language}.\n\n{prompt}"
            
            developer_content = []
            developer_content.append({
                "type": "input_text",
                "text": full_text_prompt
            })

            # Bilder hinzufügen (Format basierend auf gpt-4o angepasst)
            if images:
                for image in images:
                    base64_image = process_image(image)
                    developer_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low"
                        }
                    })

            # API-Aufruf gemäß dem bereitgestellten Snippet
            response_obj = client.responses.create(
                model="o4-mini",
                input=[
                    {
                        "role": "developer",
                        "content": developer_content
                    }
                ],
                reasoning={
                    "effort": reasoning_effort
                },
                text={"format": {"type": "text"}},
                tools=[],
                store=False
            )

            # ---- START OF CORRECTION ----
            # Extrahiere die Antwort basierend auf der tatsächlichen Objektstruktur aus dem Fehlerprotokoll.
            assistant_message = None
            # Das korrekte Attribut ist 'output', nicht 'input'.
            if hasattr(response_obj, 'output') and isinstance(response_obj.output, list):
                # Finde die Nachricht mit der Rolle 'assistant' in der output-Liste.
                for item in response_obj.output:
                    if hasattr(item, 'role') and item.role == "assistant":
                        assistant_message = item
                        break
            
            # Extrahiere den Text aus dem gefundenen Nachrichtenobjekt.
            if assistant_message and hasattr(assistant_message, 'content') and assistant_message.content:
                # Der Inhalt ist eine Liste; wir nehmen den Text des ersten Elements.
                return assistant_message.content[0].text
            else:
                st.error("Konnte keine gültige Antwort vom o4-mini Modell finden.")
                logging.error(f"Unerwartete o4-mini Antwortstruktur: {response_obj}")
                return None
            # ---- END OF CORRECTION ----
        # ---- EXISTING: Logic for Chat Completion Models (gpt-4o, etc.) ----
        else:
            user_content = [{"type": "text", "text": f"Generate questions in {selected_language}. {prompt}"}]

            if images:
                for image in images:
                    base64_image = process_image(image)
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"
                            }
                        }
                    )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096, # Adjusted for modern models, 15000 is very high
                temperature=0.6
            )
            
            # --- START of OpenAI-Side Caching Logic ---
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                cache_info_str = ""
                
                # Note: 'prompt_tokens_details' is not a standard attribute, might be from a beta feature.
                # Using getattr to prevent errors if it doesn't exist.
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


def generate_questions(user_input, learning_goals, selected_types, images, selected_language, selected_model, reasoning_effort, selected_zielniveau):
    """Generiert Fragen und implementiert Anwendungs-seitiges Caching."""
    if not client:
        st.error("Ein gültiger OpenAI-API-Schlüssel ist erforderlich, um Fragen zu generieren.")
        return

    # --- START of Application-Side Caching Logic ---
    # Use unified cache keys
    cache_key = "cached_responses"
    hash_key = "source_content_hash"
    
    # Initialize session state if it doesn't exist
    if cache_key not in st.session_state:
        st.session_state[cache_key] = {}
    if hash_key not in st.session_state:
        st.session_state[hash_key] = None
        
    # Create a hash of the current source content to detect changes
    content_to_hash = user_input
    if images:
        for img in images:
            # Use image's raw bytes for hashing if available, otherwise process it
            try:
                content_to_hash += img.tobytes()
            except:
                content_to_hash += process_image(img) # process_image returns b64 string
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
                    # Pass the list of images and reasoning effort to the API call
                    response = get_chatgpt_response(
                        full_prompt, 
                        model=selected_model, 
                        images=images, 
                        selected_language=selected_language,
                        reasoning_effort=reasoning_effort,
                        selected_zielniveau=selected_zielniveau
                    )
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
    model_options = ["gpt-4o", "gpt-4.1", "o4-mini"]
    selected_model = st.selectbox("Wählen Sie das Modell aus:", model_options, index=0)

    # NEW: Conditionally show reasoning effort selection for o4-mini
    reasoning_effort = "medium"  # Default value
    if selected_model == "o4-mini":
        st.subheader("Reasoning Effort (für o4-mini)")
        effort_options = ["low", "medium", "high"]
        reasoning_effort = st.selectbox(
            "Wählen Sie den Reasoning Effort:",
            effort_options,
            index=1  # Default to medium
        )

    st.subheader("Sprache für generierte Fragen auswählen:")
    languages = {
        "Deutsch": "German", "Englisch": "English", "Französisch": "French", 
        "Italienisch": "Italian", "Spanisch": "Spanish"
    }
    selected_language_key = st.radio("Wählen Sie die Sprache für die Ausgabe:", list(languages.keys()), index=0)
    selected_language = languages[selected_language_key]

    # NEW: Zielniveau selection
    st.subheader("Zielniveau auswählen:")
    zielniveau_labels = list(ZIELNIVEAUS_MAP.keys())
    selected_zielniveau_label = st.radio(
        "Wählen Sie das kognitive und sprachliche Niveau:",
        zielniveau_labels,
        index=2,  # Default to B2
        help="Bestimmt die sprachliche Komplexität und kognitive Anforderung der Fragen."
    )
    selected_zielniveau_text = ZIELNIVEAUS_MAP[selected_zielniveau_label]


    uploaded_files = st.file_uploader(
        "Laden Sie eine PDF, DOCX oder bis zu 10 Bilder hoch",
        type=["pdf", "docx", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    text_content = ""
    image_content_list = []

    if uploaded_files:
        # Clear cache if the set of uploaded files changes
        uploaded_filenames = sorted([f.name for f in uploaded_files])
        if 'last_uploaded_filenames' not in st.session_state or st.session_state.last_uploaded_filenames != uploaded_filenames:
            st.cache_data.clear()
            # Clear all session state caches
            for key in list(st.session_state.keys()):
                if key.startswith('cached_responses') or key.startswith('source_content_hash'):
                    del st.session_state[key]
            st.session_state.last_uploaded_filenames = uploaded_filenames
            st.info("Neue Datei(en) hochgeladen. Alle Caches wurden geleert.")

        # File validation
        if len(uploaded_files) > 10:
            st.error("Bitte laden Sie maximal 10 Bilder hoch.")
            return
        
        has_doc = any(f.name.lower().endswith(('.pdf', '.docx')) for f in uploaded_files)
        has_img = any(f.type.startswith('image/') for f in uploaded_files)
        
        if has_doc and has_img and len(uploaded_files) > 1:
            st.error("Sie können entweder eine einzelne PDF/DOCX-Datei oder mehrere Bilddateien hochladen, aber nicht mischen.")
            return
        if len([f for f in uploaded_files if has_doc]) > 1:
            st.error("Bitte laden Sie nur eine einzelne PDF- oder DOCX-Datei hoch.")
            return

        # Process files into text and/or images
        with st.spinner("Dateien werden verarbeitet..."):
            for uploaded_file in uploaded_files:
                if uploaded_file.type == "application/pdf":
                    text_from_pdf, images_from_pdf = process_pdf(uploaded_file)
                    if text_from_pdf:
                        text_content += text_from_pdf + "\n\n"
                    if images_from_pdf:
                        image_content_list.extend(images_from_pdf)
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    text_content += extract_text_from_docx(uploaded_file) + "\n\n"
                elif uploaded_file.type.startswith('image/'):
                    image_content_list.append(Image.open(uploaded_file))

    # --- UNIFIED UI SECTION ---
    if image_content_list:
        st.success(f"{len(image_content_list)} Bild(er) erfolgreich geladen.")
        # Display images in a grid
        cols = st.columns(min(len(image_content_list), 5)) # Use max 5 columns
        for idx, img in enumerate(image_content_list):
            cols[idx % 5].image(img, use_column_width=True, caption=f"Bild {idx+1}")

    user_input = st.text_area("Geben Sie Ihren Text oder Ihre Frage zum Inhalt ein:", value=text_content.strip(), height=300)
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
        elif (user_input or image_content_list) and selected_types:
            generate_questions(
                user_input, 
                learning_goals, 
                selected_types, 
                image_content_list, 
                selected_language, 
                selected_model,
                reasoning_effort,
                selected_zielniveau_text # Pass the selected level
            )
        elif not user_input and not image_content_list:
            st.warning("Bitte geben Sie Text ein oder laden Sie eine Datei hoch.")
        elif not selected_types:
            st.warning("Bitte wählen Sie mindestens einen Fragetyp aus.")

if __name__ == "__main__":
    main()