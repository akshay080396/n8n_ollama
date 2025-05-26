import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import requests
import json
import os # Import os for environment variables

# Database configuration - READ FROM ENVIRONMENT VARIABLES
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "mcp_test"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "host": os.getenv("DB_HOST", "localhost"), # Will be 'postgres-server' in Docker
    "port": os.getenv("DB_PORT", "5432")
}

# Ollama Host - READ FROM ENVIRONMENT VARIABLE
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434") # Will be 'ollama:11434' in Docker

# Build the SQLAlchemy connection string
DATABASE_URI = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"

def get_data(query):
    engine = create_engine(DATABASE_URI)
    try:
        df = pd.read_sql_query(query, engine)
    finally:
        engine.dispose()
    return df

# Helper: Get sales table schema for prompt
SALES_SCHEMA = '''
Table: sales
Columns:
- sale_id (integer, primary key)
- product_name (character varying)
- quantity (integer)
- unit_price (numeric)
- sale_date (date)
- customer_name (character varying)
- region (character varying)
''' # Corrected: Removed the extra hyphen here
def llama3_nl2sql(question):
    prompt = f"""
Given the following PostgreSQL table schema:
{SALES_SCHEMA}
Write only the SQL query (no explanation) to answer this question:
{question}
If the question is ambiguous, return a SQL query that selects all columns from the sales table.
If the question involves grouping, always use aggregate functions (like SUM, COUNT, AVG) for columns not in the GROUP BY clause.
"""
    try:
        response = requests.post(
            f"http://{OLLAMA_HOST}/api/generate", # Use OLLAMA_HOST here for Ollama API
            json={"model": "llama3", "prompt": prompt}
        )
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        lines = response.text.strip().split('\n')
        sql_parts = []
        for line in lines:
            if line.strip():
                try:
                    data = json.loads(line)
                    if "response" in data:
                        sql_parts.append(data["response"])
                except json.JSONDecodeError:
                    # Sometimes Ollama might send non-JSON lines or malformed JSON
                    pass
        sql = "".join(sql_parts).strip()
        # Remove code block markers if present
        if sql.startswith('```sql'):
            sql = sql.split('```')[1].replace('sql', '').strip()
        elif sql.startswith('```'):
            sql = sql.split('```')[1].strip()
        return sql, response.text
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to Ollama: {e}. Please ensure Ollama service is running and Llama 3 model is pulled.")
        return "", ""
    except Exception as e:
        st.error(f"An unexpected error occurred during Llama 3 interaction: {e}")
        return "", ""


st.set_page_config(layout="wide", page_title="MCP-Enhanced Postgres Dashboard")
st.markdown('<h3 style="text-align: center; margin-top: 0.5em;">MCP-Enhanced Postgres Dashboard</h3>', unsafe_allow_html=True)

# Sidebar for feature selection
st.sidebar.header('Options')
st.sidebar.markdown('---')
feature = st.sidebar.selectbox(
    'Select feature:',
    ('Llama 3',),
    key='feature_select',
)
st.sidebar.markdown('')
show_sql_query = st.sidebar.button('Show SQL Query', use_container_width=True)
st.sidebar.markdown('')

# Initialize session state for persistence
if 'last_sql' not in st.session_state:
    st.session_state['last_sql'] = ''
if 'last_raw_response' not in st.session_state:
    st.session_state['last_raw_response'] = ''
if 'last_data' not in st.session_state:
    st.session_state['last_data'] = pd.DataFrame()
if 'question_text' not in st.session_state:
    st.session_state['question_text'] = ''
if 'chart_x_col' not in st.session_state:
    st.session_state['chart_x_col'] = None
if 'chart_y_col' not in st.session_state:
    st.session_state['chart_y_col'] = None
if 'chart_type' not in st.session_state:
    st.session_state['chart_type'] = 'Bar Chart'
if 'chart_sort_order' not in st.session_state:
    st.session_state['chart_sort_order'] = 'Descending'


# Suggested questions
suggested_questions = [
    "Show the total revenue for each region.",
    "What is the total quantity sold for each product.",
    "What is the average unit price for each product.",
    "Show the total revenue for each customer.",
    "Which region had the highest total revenue.",
    "What is the total revenue for each month.",
    "List the top 5 products by total revenue.",
    "Show the number of sales for each region.",
    "What is the total revenue for each day.",
    "What is the total revenue for the year 2024.",
    "Which customer bought the most products.",
    "What is the total quantity sold for each customer.",
    "Show the average quantity sold per sale for each product.",
    "Which region had the lowest total revenue.",
    "What is the maximum unit price for each product.",
    "Show the total revenue for each product and region.",
    "List all sales where the quantity is greater than 10.",
    "Show the top 3 customers by total revenue.",
    "Show the total revenue and quantity for each product in the North region.",
    "What is the average sale amount for each customer.",
    "Show the monthly trend of total revenue.",
    "List all sales where the unit price is above 100.",
    "Which product had the highest average unit price.",
    "For each month, how many sales were made?",
    "What is the minimum quantity sold in any sale.",
    "Show the total revenue for each product and region.",
    "List all sales where the customer name is not null.",
    "Show the average unit price for each region.",
    "Which day had the highest total revenue.",
    "For each day of the week (0=Sunday, 6=Saturday), show the total sales revenue.",
    "List all sales where the region is 'East'.",
    "Show the total revenue for each customer and product.",
    "What is the total number of sales records."
]

# Table summary content
TABLE_SUMMARY = '''
<b>sales</b> table columns:<br>
<ul style="margin:0; padding-left:1em; font-size:0.9em;">
<li><b>sale_id</b>: integer, primary key</li>
<li><b>product_name</b>: character varying</li>
<li><b>quantity</b>: integer</li>
<li><b>unit_price</b>: numeric</li>
<li><b>sale_date</b>: date</li>
<li><b>customer_name</b>: character varying</li>
<li><b>region</b>: character varying</li>
</ul>
'''

# Show SQL query in sidebar only if button pressed
if show_sql_query and st.session_state['last_sql']:
    st.sidebar.markdown('**Generated SQL Query:**')
    st.sidebar.code(st.session_state['last_sql'], language='sql')

# Table Summary expander
with st.sidebar.expander('Table Summary', expanded=False):
    st.markdown(f'<div style="font-size:0.85em;">{TABLE_SUMMARY}</div>', unsafe_allow_html=True)

# Move Show debug info checkbox and debug output to the very bottom
st.sidebar.markdown('---')
show_debug = st.sidebar.checkbox('Show debug info')
if show_debug and st.session_state['last_raw_response']:
    st.sidebar.markdown('**Debug**')
    st.sidebar.write(st.session_state['last_raw_response'])

if feature == 'Llama 3':
    st.markdown('<h4 style="text-align: center;">Ask a question about the sales table</h4>', unsafe_allow_html=True)
    question = st.text_area('Enter your question:')
    run_prompt = st.button('Run Prompt Query', use_container_width=True)
    selected_suggestion = st.selectbox('Or pick a suggested question:', [''] + suggested_questions)
    run_suggested = st.button('Run Suggested Query', use_container_width=True)

    if (run_prompt and question.strip()) or (run_suggested and selected_suggestion.strip()):
        query_to_use = question if run_prompt else selected_suggestion
        with st.spinner('Generating SQL with Llama 3...'):
            try:
                sql, raw_response = llama3_nl2sql(query_to_use)
                if not sql:
                    st.error("Llama 3 did not return a SQL query. Please try rephrasing your question or check Ollama logs.")
                else:
                    data = get_data(sql)
                    st.session_state['last_sql'] = sql
                    st.session_state['last_raw_response'] = raw_response
                    st.session_state['last_data'] = data

                    # Initialize chart selection for new data if needed
                    if not data.empty:
                        if st.session_state['chart_x_col'] not in data.columns:
                            st.session_state['chart_x_col'] = data.columns[0]
                        if st.session_state['chart_y_col'] not in data.columns:
                            st.session_state['chart_y_col'] = data.columns[1]

            except Exception as e:
                st.error(f"Error: {e}")

    # Main area: show results and interactive visualization
    data = st.session_state['last_data']
    if not data.empty:
        # Chart options below the graph, fully interactive
        st.markdown('---')
        st.markdown('**Chart Options**')
        # Ensure that selected columns exist in the current DataFrame
        default_x_index = data.columns.get_loc(st.session_state['chart_x_col']) if st.session_state['chart_x_col'] in data.columns else 0
        default_y_index = data.columns.get_loc(st.session_state['chart_y_col']) if st.session_state['chart_y_col'] in data.columns else 1

        x_col = st.selectbox('X axis:', data.columns, index=default_x_index, key='x_col')
        if x_col != st.session_state['chart_x_col']:
            st.session_state['chart_x_col'] = x_col

        y_col = st.selectbox('Y axis:', data.columns, index=default_y_index, key='y_col')
        if y_col != st.session_state['chart_y_col']:
            st.session_state['chart_y_col'] = y_col

        chart_type = st.selectbox('Chart type:', ['Bar Chart', 'Line Chart', 'Pie Chart'], index=['Bar Chart', 'Line Chart', 'Pie Chart'].index(st.session_state['chart_type']), key='chart_type')
        if chart_type != st.session_state['chart_type']:
            st.session_state['chart_type'] = chart_type

        sort_order = st.selectbox('Sort order:', ['Descending', 'Ascending'], index=['Descending', 'Ascending'].index(st.session_state['chart_sort_order']), key='sort_order')
        if sort_order != st.session_state['chart_sort_order']:
            st.session_state['chart_sort_order'] = sort_order

        # Render the chart
        if st.session_state['chart_y_col'] in data.columns: # Ensure y_col exists before sorting
            sorted_data = data.sort_values(by=st.session_state['chart_y_col'], ascending=(st.session_state['chart_sort_order'] == 'Ascending'))
        else:
            sorted_data = data # Or handle error if y_col not found

        if st.session_state['chart_type'] == 'Bar Chart':
            fig = px.bar(sorted_data, x=st.session_state['chart_x_col'], y=st.session_state['chart_y_col'], color=st.session_state['chart_x_col'], title=f"{st.session_state['chart_y_col']} by {st.session_state['chart_x_col']}", text_auto=True)
            fig.update_traces(textposition='outside')
            fig.update_layout(clickmode='event+select')
            st.plotly_chart(fig, use_container_width=True)
        elif st.session_state['chart_type'] == 'Line Chart':
            fig = px.line(sorted_data, x=st.session_state['chart_x_col'], y=st.session_state['chart_y_col'], markers=True, title=f"{st.session_state['chart_y_col']} by {st.session_state['chart_x_col']}", text=st.session_state['chart_y_col'])
            fig.update_traces(textposition='top center')
            fig.update_layout(clickmode='event+select')
            st.plotly_chart(fig, use_container_width=True)
        elif st.session_state['chart_type'] == 'Pie Chart':
            fig = px.pie(sorted_data, names=st.session_state['chart_x_col'], values=st.session_state['chart_y_col'], title=f"{st.session_state['chart_y_col']} by {st.session_state['chart_x_col']}", hole=0.3)
            fig.update_traces(textinfo='percent+label+value')
            st.plotly_chart(fig, use_container_width=True)
        # Data table at the bottom
        st.dataframe(data, use_container_width=True, height=400)