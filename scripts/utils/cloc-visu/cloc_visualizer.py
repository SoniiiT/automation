import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="CLOC Visualizer", layout="wide")

st.title("CLOC Data Visualizer")
st.markdown("""
Dieses Tool ermöglicht die Visualisierung von CLOC (Count Lines of Code) Daten.
Laden Sie Ihre CSV-Datei hoch oder fügen Sie die Daten direkt ein.
""")

# --- Sidebar: Data Input ---
st.sidebar.header("1. Daten Import")
input_method = st.sidebar.radio("Eingabemethode:", ["Datei Upload", "Text Einfügen"])

df = None

def parse_data(content):
    try:
        # Try reading with flexible separator
        # Assessing columns based on the user's example:
        # __ALL__	Dockerfile	9	67	47	108
        # We assume headers might be missing or specific.
        # Let's try to detect if header exists. usually CLOC csv has headers.
        # If not, we assign names.
        
        # First read raw to see first line
        first_line = content.strip().split('\n')[0]
        
        # Heuristic: If first line contains "Language", it has headers.
        # Otherwise, assign manually based on 6 columns seen in example.
        names = None
        header = 0
        if "Language" not in first_line and "files" not in first_line:
            header = None
            names = ["Scope", "Language", "nFiles", "Blank", "Comment", "Code"]
            
        data = pd.read_csv(io.StringIO(content), sep=None, engine='python', header=header, names=names)
        
        # Determine strict numeric columns
        numeric_cols = ["Code", "Comment", "Blank", "nFiles"]
        if names: # If we assigned names
            pass
        else: 
            # If we read headers, we need to identify the columns.
            # Common cloc headers: language, files, blank, comment, code
            # Normalize to our standard
            data.columns = [c.strip() for c in data.columns]
            
            # Simple fuzzy matching or just let user mapping handle it later if needed?
            # For this specific request, we'll try to map standard ones.
            pass
            
        return data
    except Exception as e:
        st.error(f"Fehler beim Parsen der Daten: {e}")
        return None

if input_method == "Datei Upload":
    uploaded_file = st.sidebar.file_uploader("CSV Datei wählen", type=["csv", "txt"])
    if uploaded_file is not None:
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
        raw_data = stringio.read()
        df = parse_data(raw_data)
else:
    text_input = st.sidebar.text_area("Daten hier einfügen", height=200, 
        help="Kopieren Sie den Inhalt Ihrer CLOC Ausgabe hier rein.",
        value="""scope	language	files	blank	comment	code
__ALL__	Dockerfile	9	67	47	108
__ALL__	HTML	1	0	20	28
__ALL__	INI	1	2	0	12
__ALL__	JavaScript	14	36	628	960
__ALL__	JSON	22	33	0	29081
__ALL__	Markdown	23	357	0	915
__ALL__	PowerShell	13	609	809	1393
__ALL__	Python	99	3159	4594	9947
__ALL__	SCSS	3	30	7	149
__ALL__	SUM	622	9262	13118	115034
__ALL__	SUM	311	4631	6559	57517
__ALL__	SVG	1	0	0	3
__ALL__	Vuejs Component	63	96	3	11910
__ALL__	XML	1	0	0	2
__ALL__	YAML	61	242	451	3009
itc-api-nx-adm-ui	HTML	1	0	20	28
itc-api-nx-adm-ui	INI	1	2	0	12
itc-api-nx-adm-ui	JavaScript	14	36	628	960
itc-api-nx-adm-ui	JSON	2	0	0	83
itc-api-nx-adm-ui	Markdown	1	52	0	127
itc-api-nx-adm-ui	SCSS	3	30	7	149
itc-api-nx-adm-ui	SUM	87	216	658	13274
itc-api-nx-adm-ui	SVG	1	0	0	3
itc-api-nx-adm-ui	Vuejs Component	63	96	3	11910
itc-api-nx-adm-ui	XML	1	0	0	2
itc-api-nx-srvc-atsk	Dockerfile	1	7	5	12
itc-api-nx-srvc-atsk	JSON	4	3	0	4327
itc-api-nx-srvc-atsk	Markdown	1	9	0	15
itc-api-nx-srvc-atsk	Python	9	530	403	1924""")
    if text_input:
        df = parse_data(text_input)

if df is not None:
    # --- Column Handling ---
    st.sidebar.header("2. Spalten Zuordnung")
    all_cols = list(df.columns)
    
    # Try to find defaults
    def get_col_index(columns, search_terms, default_idx=0):
        cols_lower = [str(c).lower() for c in columns]
        for term in search_terms:
            if term.lower() in cols_lower:
                return cols_lower.index(term.lower())
        return default_idx if 0 <= default_idx < len(columns) else 0

    # We need: Language column, and a Value column (Code usually)
    lang_idx = get_col_index(all_cols, ["Language", "Sprache"], 1)
    col_lang = st.sidebar.selectbox("Sprache Spalte (Beschreibung)", all_cols, index=lang_idx)
    
    # Try to identify Scope column
    scope_idx = get_col_index(all_cols, ["Scope", "scope"], 0)
    col_scope = st.sidebar.selectbox("Scope Spalte (Gruppierung)", all_cols, index=scope_idx)

    # Metric Columns Selection
    metric_options = [c for c in all_cols if c not in [col_lang, col_scope]]
    
    # Default selection: Code, Comment, Blank if available
    default_metrics = []
    for m in ["Code", "Question", "Blank", "comment", "blank", "code"]:
        idx = get_col_index(metric_options, [m], -1)
        if idx != -1:
            default_metrics.append(metric_options[idx])
    
    # Remove duplicates while preserving order
    default_metrics = list(dict.fromkeys(default_metrics))
    if not default_metrics and metric_options:
        default_metrics = [metric_options[-1]]

    selected_metrics = st.sidebar.multiselect("Metriken auswählen", metric_options, default=default_metrics)
    if not selected_metrics:
        st.warning("Bitte wählen Sie mindestens eine Metrik aus.")
        st.stop()
    
    # --- Filtering ---
    # Separate SUM rows
    is_sum_row = df[col_lang].astype(str).str.contains("SUM", case=False, na=False)
    # df_sum = df[is_sum_row] # Not used currently
    df_langs = df[~is_sum_row]
    
    # Scope Filtering
    unique_scopes = sorted(df_langs[col_scope].unique())
    selected_scope = st.sidebar.selectbox("Scope Filter (Bereich)", unique_scopes, index=unique_scopes.index("__ALL__") if "__ALL__" in unique_scopes else 0)
    
    df_scoped = df_langs[df_langs[col_scope] == selected_scope].copy()

    # Aggregate by language in case of duplicates
    # Ensure value columns are numeric
    for col in selected_metrics:
        try:
            df_scoped[col] = pd.to_numeric(df_scoped[col])
        except Exception as e:
            st.error(f"Die Spalte '{col}' enthält nicht-numerische Daten. Bitte korrigieren.")
            st.stop()
            
    clean_df = df_scoped.groupby(col_lang, as_index=False)[selected_metrics].sum()

    # --- Sidebar: Visualization Config ---
    st.sidebar.header("3. Diagramm Einstellungen")
    
    # Language Selection
    unique_langs = sorted(clean_df[col_lang].unique())
    selected_langs = st.sidebar.multiselect("Sprachen auswählen", unique_langs, default=unique_langs)
    
    if not selected_langs:
        st.warning("Bitte wählen Sie mindestens eine Sprache aus.")
        st.stop()
        
    plot_df = clean_df[clean_df[col_lang].isin(selected_langs)].copy()
    
    # Calculate Total for sorting if multiple metrics
    plot_df['Total_Selected'] = plot_df[selected_metrics].sum(axis=1)

    # Sort data
    sort_order = st.sidebar.radio("Sortierung", ["Absteigend", "Aufsteigend", "Alphabetisch"])
    if sort_order == "Absteigend":
        plot_df = plot_df.sort_values(by='Total_Selected', ascending=False)
    elif sort_order == "Aufsteigend":
        plot_df = plot_df.sort_values(by='Total_Selected', ascending=True)
    else:
        plot_df = plot_df.sort_values(by=col_lang)
        
    chart_type = st.sidebar.selectbox("Diagramm Typ", ["Balkendiagramm (Horizontal)", "Balkendiagramm (Vertikal)", "Kreisdiagramm", "Donut"])
    
    # Label Format
    label_format = st.sidebar.radio("Beschriftung Format", ["Absolut", "Prozent", "Beides"])
    
    # Sum Configuration
    show_sum = st.sidebar.checkbox("Gesamtsumme anzeigen", value=True)
    sum_text_custom = st.sidebar.text_input("Beschriftung der Summe", "Total:")
    
    # Position sliders
    st.sidebar.subheader("Summe Positionierung")
    sum_pos_x = st.sidebar.slider("X Position", 0.0, 1.5, 0.5, 0.05)
    sum_pos_y = st.sidebar.slider("Y Position", -0.5, 1.5, 1.05, 0.05)
    sum_font_size = st.sidebar.slider("Schriftgröße", 8, 24, 12)
    
    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Color palette
    # Use distinct colors if single metric, or specific palette if stacked?
    # Actually for stacked charts (multi metrics per language), we need colors per metric.
    # For single metric per language (classic), we need colors per language.
    
    is_multi_metric = len(selected_metrics) > 1
    
    if chart_type in ["Balkendiagramm (Horizontal)", "Balkendiagramm (Vertikal)"]:
        if is_multi_metric:
            # Stacked or Grouped? Stacked is usually better for "Total Code" composition.
            plot_df.set_index(col_lang)[selected_metrics].plot(
                kind='barh' if "Horizontal" in chart_type else 'bar', 
                stacked=True, 
                ax=ax,
                colormap='viridis'
            )
            ax.set_title(f"Code Metrics per {col_lang}")
            
            # Labels for segments? A bit complex with matplotlib standard plot. 
            # We will rely on axis and legend.
            ax.legend(title="Metrik")
            
        else:
            metric = selected_metrics[0]
            colors = plt.cm.Paired(range(len(plot_df)))
            if "Horizontal" in chart_type:
                bars = ax.barh(plot_df[col_lang], plot_df[metric], color=colors)
                # Labels on bars
                for bar in bars:
                    width = bar.get_width()
                    label_text = ""
                    if label_format in ["Absolut", "Beides"]:
                        label_text += f"{width:,.0f}"
                    if label_format in ["Prozent", "Beides"]:
                        total = plot_df['Total_Selected'].sum()
                        pct = width / total * 100
                        if label_format == "Beides": label_text += " "
                        label_text += f"({pct:.1f}%)"
                        
                    if label_text:
                        ax.text(width, bar.get_y() + bar.get_height()/2, 
                                f" {label_text}", 
                                va='center')
                                
            else:
                bars = ax.bar(plot_df[col_lang], plot_df[metric], color=colors)
                plt.xticks(rotation=45, ha='right')
                # Labels on bars
                for bar in bars:
                    height = bar.get_height()
                    label_text = ""
                    if label_format in ["Absolut", "Beides"]:
                        label_text += f"{height:,.0f}"
                    if label_format in ["Prozent", "Beides"]:
                        total = plot_df['Total_Selected'].sum()
                        pct = height / total * 100
                        if label_format == "Beides": label_text += " "
                        label_text += f"({pct:.1f}%)"
                        
                    if label_text:
                        ax.text(bar.get_x() + bar.get_width()/2, height, 
                                f"{label_text}", 
                                ha='center', va='bottom')

        # Invert y axis for horizontal if needed
        if "Horizontal" in chart_type and sort_order == "Absteigend":
            ax.invert_yaxis()

    elif chart_type in ["Kreisdiagramm", "Donut"]:
        # Pie charts really only work well with 1 dimension of values.
        # If multiple metrics selected, we sum them up per language (Total_Selected).
        vals = plot_df['Total_Selected']
        labels = plot_df[col_lang]
        
        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = int(round(pct*total/100.0))
                text = ""
                if label_format in ["Prozent", "Beides"]:
                    text += f"{pct:.1f}%"
                if label_format in ["Absolut", "Beides"]:
                    if text: text += "\n"
                    text += f"{val:,.0f}"
                return text if text else ""
            return my_autopct

        wedges, texts, autotexts = ax.pie(vals, labels=labels, autopct=make_autopct(vals), startangle=90, colors=plt.cm.Paired(range(len(plot_df))))
        ax.axis('equal')
        if chart_type == "Donut":
            centre_circle = plt.Circle((0,0),0.70,fc='white')
            fig.gca().add_artist(centre_circle)
            
        if is_multi_metric:
            ax.set_title(f"Total ({'+'.join(selected_metrics)}) per {col_lang}")

    # Calculate Total Sum
    current_sum = plot_df['Total_Selected'].sum()
    
    if show_sum:
        sum_label = f"{sum_text_custom} {current_sum:,.0f}"
        if chart_type in ["Kreisdiagramm", "Donut"]:
             ax.text(sum_pos_x, sum_pos_y, sum_label, transform=ax.transAxes, 
                     fontsize=sum_font_size, ha='center', va='center', 
                     bbox=dict(facecolor='white', alpha=0.5, edgecolor='gray', boxstyle='round,pad=0.5'))
        else:
             ax.text(sum_pos_x, sum_pos_y, sum_label, transform=ax.transAxes, 
                     fontsize=sum_font_size, ha='center', va='center',
                     bbox=dict(facecolor='white', alpha=0.5, edgecolor='gray', boxstyle='round,pad=0.5'))

    plt.tight_layout()
    st.pyplot(fig)
    
    # --- Download ---
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    st.download_button(
        label="Diagramm als Bild herunterladen",
        data=img_buffer,
        file_name="cloc_visualisierung.png",
        mime="image/png"
    )

    # Show data table
    with st.expander("Rohdaten ansehen"):
        st.dataframe(plot_df)

else:
    st.info("Bitte laden Sie Daten hoch, um zu beginnen.")
