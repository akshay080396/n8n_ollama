import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sqlalchemy import create_engine # Will be replaced by pymongo
import pymongo # Added for MongoDB
from bson import ObjectId # Import ObjectId directly from bson
import requests
import json
import os # Import os for environment variables

# Database configuration - READ FROM ENVIRONMENT VARIABLES
# MYSQL DB_CONFIG (commented out, will be replaced)
# DB_CONFIG = {
# "dbname": os.getenv("DB_NAME", "mcp_test"),
# "user": os.getenv("DB_USER", "mysqluser"),
# "password": os.getenv("DB_PASSWORD", "mysqlpassword"),
# "host": os.getenv("DB_HOST", "localhost"), # Will be 'mysql-server' in Docker
# "port": os.getenv("DB_PORT", "3306")
# }

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "admin")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "ordercollections")

# Ollama Host - READ FROM ENVIRONMENT VARIABLE
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434") # Will be 'ollama:11434' in Docker

# SQLAlchemy connection string (commented out)
# DATABASE_URI = f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"

def get_mongo_data(query_dict):
    client = None
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]

        # query_dict can be {"find": <filter_doc>, "projection": <projection_doc>}
        # or {"aggregate": <pipeline_list>}
        if "find" in query_dict:
            cursor = collection.find(query_dict.get("find", {}), query_dict.get("projection"))
        elif "aggregate" in query_dict:
            cursor = collection.aggregate(query_dict.get("aggregate", []))
        else:
            # Default to find all if query is not structured as expected
            st.warning("Query structure not recognized, attempting to find all documents.")
            cursor = collection.find({})
        
        df = pd.DataFrame(list(cursor))

        # Convert ObjectId columns to string for better display in Streamlit/Plotly
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, ObjectId)).any():
                df[col] = df[col].astype(str)
            # Handle nested dicts/lists if they cause issues with plotting (optional: flatten or extract)
            # For now, let Pandas handle them; may need specific handling later
        
        # If '_id' is an ObjectId and now string, ensure it doesn't cause issues if used as index
        if '_id' in df.columns and isinstance(df['_id'].iloc[0] if not df.empty else None, str):
             pass # Already converted

    except pymongo.errors.ConnectionFailure as e:
        st.error(f"MongoDB Connection Error: {e}")
        df = pd.DataFrame()
    except pymongo.errors.OperationFailure as e:
        st.error(f"MongoDB Query Error: {e}")
        df = pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching MongoDB data: {e}")
        df = pd.DataFrame()
    finally:
        if client:
            client.close()
    return df

# Helper: Get MongoDB collection schema for prompt
MONGO_COLLECTION_SCHEMA = """
Collection: ordercollections
Description: Contains detailed information about customer orders, including buyer details, product information, payment status, and delivery tracking.
Fields (use dot notation for nested fields in your queries where appropriate):
- _id (ObjectId, primary key)
- paymentStatus (string, e.g., "SUCCESS", "PENDING", "FAILED")
- userId (string, identifier for the user who placed the order)
- orderId (number, unique numeric identifier for the order)
- status (string, current status of the order, e.g., "DELIVERED", "SHIPPED", "PROCESSING", "PENDING")
- buyerDetails (object):
  - permanentAddress (object):
    - firstName (string)
    - lastName (string)
    - emailId (string)
    - city (string)
    - country (string)
    - postalCode (string)
- createdAt (ISODate, timestamp of when the order was created)
- updatedAt (ISODate, timestamp of when the order was last updated)
- pickupDetails (object, details for order pickup if applicable):
  - firstName (string)
  - city (string)
  - warehouseAddressName (string)
- orderDetails (object):
  - products (array of objects, list of products in the order):
    - productName (string)
    - sku (string)
    - taxRate (number)
    - unitPrice (number)
    - quantity (number)
  - orderDate (ISODate, timestamp of when the order was placed)
  - paymentMode (string, e.g., "Prepaid", "COD")
  - orderChannel (string, e.g., "Instagram", "Website", "Facebook")
  - totalPrice (number, total monetary value of the order)
  - totalWeight (number, total weight of all products in the order)
- estimatedDeliveryPartnerCost (number)
- orderTrackingData (object, information from the delivery partner):
  - partnerType (string, e.g., "LITTLE", "UBER")
  - orderData (object):
    - distance (string, often a number as string, e.g., "10.5")
    - time (string, often a number as string, e.g., "30" for minutes)
    - driver.name (string)
- partnerCostWithCommission (number)
- paymentId (ObjectId, reference to a payment document/transaction)
- percentageCommission (number)
- actualCostToPayPartner (number)

Querying Notes:
- For `find` queries, provide a filter document, e.g., `{ "status": "DELIVERED" }`. Optionally, a projection document.
- For `aggregate` queries, provide a list of pipeline stages, e.g., `[ { "$match": { "status": "DELIVERED" } }, { "$group": { "_id": "$orderDetails.orderChannel", "totalRevenue": { "$sum": "$orderDetails.totalPrice" } } } ]`.
- When asked for totals, averages, counts, use the aggregation framework. For example, to count orders by status: `[ { "$group": { "_id": "$status", "count": { "$sum": 1 } } } ]`.
- To query fields within nested objects, use dot notation, e.g., `{ "orderDetails.orderChannel": "Instagram" }`.
- To query elements within an array (like `orderDetails.products`), you might need `$unwind` in an aggregation or use dot notation with array indexes if applicable, or query conditions like `$elemMatch`.
- If the question is ambiguous or too complex for a simple find, try to formulate an aggregation pipeline. If a listing is asked, usually a find query is enough.
"""

def llama3_nl_to_mongo_query(question):
    prompt = f"""
Given the following MongoDB collection schema:
{MONGO_COLLECTION_SCHEMA}

You are an AI assistant that translates natural language questions into MongoDB queries.
The user wants to query the 'ordercollections' collection.
Respond with ONLY the MongoDB query object (for find) or pipeline array (for aggregate) in a valid JSON format.
Do NOT use `db.collection.find(...)` or `db.collection.aggregate(...)`.
Output ONLY the JSON filter/projection for find, or the JSON array for aggregate.

For example:
If the question is "Show all delivered orders", the response should be:
`{{"find": {{"status": "DELIVERED"}}}}`

If the question is "What are the total sales for each order channel?", the response should be:
`{{"aggregate": [ {{"$group": {{"_id": "$orderDetails.orderChannel", "totalSales": {{"$sum": "$orderDetails.totalPrice"}}}} }} ] }}`

If the question is "List product names and quantities for orderId 123", the response should be:
`{{"find": {{"orderId": 123}}, "projection": {{"_id": 0, "orderDetails.products.productName": 1, "orderDetails.products.quantity": 1}}}}`

If the question is ambiguous or you cannot generate a query, return an empty JSON object: `{{}}`.

User question: "{question}"

MongoDB Query (JSON only):
"""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False, "format": "json"} # Added stream: False and format: json
        )
        response.raise_for_status()

        # Assuming Ollama with "format":"json" directly returns a JSON object string in "response"
        raw_response_text = response.text # For debugging
        
        # Attempt to parse the entire response as JSON if format="json" worked as expected
        try:
            json_response = response.json()
            query_str = json_response.get("response", "{}") # The actual query from Llama3
        except json.JSONDecodeError:
            # Fallback for models/versions of Ollama that might not perfectly adhere to format="json"
            # or if the output is still line-delimited JSON objects
            lines = response.text.strip().split('\\n') # Split by escaped newlines if they are present
            if not lines: lines = response.text.strip().split('\n')

            full_json_str = ""
            for line in lines:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            full_json_str += data["response"]
                        elif not full_json_str and line.strip().startswith('{') and line.strip().endswith('}'): # if a single line is the full json
                            full_json_str = line.strip()
                            break 
                    except json.JSONDecodeError:
                        # Accumulate if it's part of a larger JSON string
                        if not full_json_str: # if we haven't started accumulating, this might be the start
                             if line.strip().startswith('{') or line.strip().startswith('['):
                                full_json_str += line.strip()
                        elif full_json_str: # if we have started, just append
                            full_json_str += line.strip()
            query_str = full_json_str if full_json_str else "{}"


        # Final clean up for the query string from Llama3
        # Remove potential markdown, leading/trailing whitespace
        if query_str.startswith("```json"):
            query_str = query_str.split("```json")[1].strip()
        if query_str.startswith("```"):
            query_str = query_str.split("```")[1].strip()
        if query_str.endswith("```"):
            query_str = query_str.rsplit("```", 1)[0].strip()
        
        query_str = query_str.replace('\\n', '\n').replace('\\"', '"') # Unescape newlines and quotes

        # Try to parse the cleaned string into a Python dictionary
        parsed_query_dict = {}
        if query_str:
            try:
                parsed_query_dict = json.loads(query_str)
            except json.JSONDecodeError as e:
                st.error(f"Llama 3 returned a non-JSON response for the query: {query_str}. Error: {e}")
                return {}, raw_response_text # Return empty dict and raw response
        
        # Validate if it's a find or aggregate structure
        if not (("find" in parsed_query_dict and isinstance(parsed_query_dict["find"], dict)) or \
                ("aggregate" in parsed_query_dict and isinstance(parsed_query_dict["aggregate"], list))):
            if parsed_query_dict: # If it parsed but not in expected structure
                 st.warning(f"Llama 3 query structure not recognized: {parsed_query_dict}. Attempting to use as find filter.")
                 # Fallback: assume it's a find filter if it's a dict and not empty
                 if isinstance(parsed_query_dict, dict) and parsed_query_dict:
                     return {"find": parsed_query_dict}, raw_response_text
                 else: # if not a dict or empty, then invalid
                    st.error("Llama 3 query is not a valid find filter or aggregate pipeline.")
                    return {}, raw_response_text # Return empty dict and raw response
            # If parsed_query_dict is empty from the start, it means Llama3 likely intended no query
            # or there was an error it couldn't recover from.

        return parsed_query_dict, raw_response_text

    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to Ollama: {e}. Please ensure Ollama service is running and Llama 3 model is pulled.")
        return {}, ""
    except Exception as e:
        st.error(f"An unexpected error occurred during Llama 3 interaction: {e}")
        return {}, ""


st.set_page_config(layout="wide", page_title="MCP-Enhanced MongoDB Dashboard") # Updated title
st.markdown('<h3 style="text-align: center; margin-top: 0.5em;">MCP-Enhanced MongoDB Dashboard</h3>', unsafe_allow_html=True) # Updated title

# Sidebar for feature selection
st.sidebar.header('Options')
st.sidebar.markdown('---')
feature = st.sidebar.selectbox(
    'Select feature:',
    ('Llama 3',), # Kept Llama 3 as the only feature for now
    key='feature_select',
)
st.sidebar.markdown('')
show_mongo_query = st.sidebar.button('Show MongoDB Query', use_container_width=True) # Renamed button
st.sidebar.markdown('')

# Initialize session state for persistence
if 'last_mongo_query_dict' not in st.session_state: # Renamed
    st.session_state['last_mongo_query_dict'] = {}
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


# Suggested questions for MongoDB
suggested_questions = [
    "Show total revenue for each order channel.",
    "What is the total quantity of 'Paper' sold?", # Assumes 'Paper' is a common product
    "List orders with status 'DELIVERED'.",
    "What is the average totalPrice for orders from 'Instagram'?",
    "Which city has the most orders for buyerDetails?", # Example using buyerDetails
    "Count orders by paymentStatus.",
    "Show product names and quantities for orderId 1.", # Example: specific orderId
    "What are the top 5 products by total quantity sold?", # Needs aggregation and unwind
    "Show all orders created yesterday.", # Needs date handling, Llama3 needs to be smart here
    "List all orders with a totalPrice greater than 500.",
    "What is the total estimated delivery partner cost for 'LITTLE' partner type?",
    "Show the status of orderId 1." # Example for a specific orderId
]

# Collection summary content
COLLECTION_SUMMARY = '''
<b>ordercollections</b> collection fields (selected):<br>
<ul style="margin:0; padding-left:1em; font-size:0.9em;">
<li><b>_id</b>: ObjectId (Primary Key)</li>
<li><b>orderId</b>: Number (Unique order ID)</li>
<li><b>paymentStatus</b>: String (e.g., SUCCESS, PENDING)</li>
<li><b>status</b>: String (e.g., DELIVERED, SHIPPED)</li>
<li><b>userId</b>: String</li>
<li><b>buyerDetails.permanentAddress.city</b>: String</li>
<li><b>buyerDetails.permanentAddress.country</b>: String</li>
<li><b>createdAt</b>: ISODate (Order creation timestamp)</li>
<li><b>orderDetails.orderDate</b>: ISODate (Date of order placement)</li>
<li><b>orderDetails.products</b>: Array (List of products)</li>
<li>  &#溶解; <b>productName</b>: String</li>
<li>  &#溶解; <b>quantity</b>: Number</li>
<li>  &#溶解; <b>unitPrice</b>: Number</li>
<li><b>orderDetails.orderChannel</b>: String (e.g., Instagram)</li>
<li><b>orderDetails.totalPrice</b>: Number (Total order value)</li>
<li><b>orderDetails.paymentMode</b>: String</li>
</ul>
'''

# Show MongoDB query in sidebar only if button pressed
if show_mongo_query and st.session_state['last_mongo_query_dict']: # Renamed variable and button
    st.sidebar.markdown('**Generated MongoDB Query (JSON):**') # Updated title
    # Pretty print the JSON query
    try:
        st.sidebar.code(json.dumps(st.session_state['last_mongo_query_dict'], indent=2), language='json')
    except Exception as e:
        st.sidebar.text(f"Error formatting query for display: {e}")
        st.sidebar.text(str(st.session_state['last_mongo_query_dict']))


# Collection Summary expander
with st.sidebar.expander('Collection Summary', expanded=False): # Renamed
    st.markdown(f'<div style="font-size:0.85em;">{COLLECTION_SUMMARY}</div>', unsafe_allow_html=True)

# Move Show debug info checkbox and debug output to the very bottom
st.sidebar.markdown('---')
show_debug = st.sidebar.checkbox('Show debug info')
if show_debug and st.session_state['last_raw_response']:
    st.sidebar.markdown('**Llama 3 Raw Response:**') # Updated title
    st.sidebar.text_area("Raw Output", st.session_state['last_raw_response'], height=200) # Use text_area for better display

if feature == 'Llama 3':
    st.markdown('<h4 style="text-align: center;">Ask a question about the ordercollections collection</h4>', unsafe_allow_html=True) # Updated
    question = st.text_area('Enter your question:', key="mongo_question_text_area") # Added key to avoid conflict if any
    run_prompt = st.button('Run Prompt Query', use_container_width=True)
    selected_suggestion = st.selectbox('Or pick a suggested question:', [''] + suggested_questions)
    run_suggested = st.button('Run Suggested Query', use_container_width=True)

    if (run_prompt and question.strip()) or (run_suggested and selected_suggestion.strip()):
        query_to_use = question if (run_prompt and question.strip()) else selected_suggestion
        if query_to_use: # Ensure query_to_use is not empty
            with st.spinner('Generating MongoDB query with Llama 3...'): # Updated
                try:
                    mongo_query_dict, raw_response = llama3_nl_to_mongo_query(query_to_use)
                    st.session_state['last_raw_response'] = raw_response # Save raw response immediately

                    if not mongo_query_dict or (not mongo_query_dict.get("find") and not mongo_query_dict.get("aggregate")):
                        st.error("Llama 3 did not return a valid MongoDB query structure. Please try rephrasing your question or check Ollama logs.")
                        # No data to fetch if query is invalid
                    else:
                        st.session_state['last_mongo_query_dict'] = mongo_query_dict # Save parsed query
                        with st.spinner('Fetching data from MongoDB...'): # Added spinner for data fetching
                            data = get_mongo_data(mongo_query_dict) # Use new data fetching function
                        st.session_state['last_data'] = data

                        # Initialize chart selection for new data if needed
                        if not data.empty:
                            # Attempt to find suitable default columns robustly
                            if data.columns.empty: # Should not happen if data is not empty, but defensive
                                st.session_state['chart_x_col'] = None
                                st.session_state['chart_y_col'] = None
                            else:
                                # Prefer existing choices if still valid
                                if st.session_state['chart_x_col'] not in data.columns:
                                    st.session_state['chart_x_col'] = data.columns[0]
                                if st.session_state['chart_y_col'] not in data.columns:
                                    # Try to pick a numeric column for Y if X is categorical, or second col
                                    numeric_cols = data.select_dtypes(include=np.number).columns
                                    if len(data.columns) > 1:
                                        potential_y = data.columns[1]
                                        if not numeric_cols.empty and potential_y not in numeric_cols : # if second col not numeric, pick first numeric
                                             st.session_state['chart_y_col'] = numeric_cols[0] if st.session_state['chart_x_col'] != numeric_cols[0] else (numeric_cols[1] if len(numeric_cols) > 1 else data.columns[1])
                                        else: # Second col is fine or no numeric cols
                                            st.session_state['chart_y_col'] = potential_y
                                    elif not numeric_cols.empty : # Only one col, but it's numeric
                                        st.session_state['chart_y_col'] = numeric_cols[0]
                                    else: # Only one col, not numeric (or no cols)
                                        st.session_state['chart_y_col'] = data.columns[0]
                        else: # Data is empty
                            st.info("The query returned no data.")
                            # Potentially clear chart columns or leave them as is
                            # st.session_state['chart_x_col'] = None
                            # st.session_state['chart_y_col'] = None


                except Exception as e:
                    st.error(f"Error during query generation or data fetching: {e}")
                    st.session_state['last_data'] = pd.DataFrame() # Clear data on error

    # Main area: show results and interactive visualization
    data = st.session_state['last_data']
    if not data.empty:
        # Chart options below the graph, fully interactive
        st.markdown('---')
        st.markdown('**Chart Options**')
        
        # Ensure that selected columns exist in the current DataFrame
        # More robust default index finding
        current_cols = data.columns.tolist()
        default_x_idx = 0
        if st.session_state['chart_x_col'] in current_cols:
            default_x_idx = current_cols.index(st.session_state['chart_x_col'])
        elif current_cols: # If previous x_col not found, default to first
            st.session_state['chart_x_col'] = current_cols[0]
        
        default_y_idx = 0
        if len(current_cols) > 1: default_y_idx = 1 # Default to second column if available
        if st.session_state['chart_y_col'] in current_cols:
            default_y_idx = current_cols.index(st.session_state['chart_y_col'])
        elif current_cols: # If previous y_col not found
            if len(current_cols) > 1:
                 st.session_state['chart_y_col'] = current_cols[1]
            else: # Only one column available
                 st.session_state['chart_y_col'] = current_cols[0]
                 default_y_idx = 0


        x_col = st.selectbox('X axis:', data.columns, index=default_x_idx, key='mongo_x_col')
        if x_col != st.session_state['chart_x_col']:
            st.session_state['chart_x_col'] = x_col

        y_col = st.selectbox('Y axis:', data.columns, index=default_y_idx, key='mongo_y_col')
        if y_col != st.session_state['chart_y_col']:
            st.session_state['chart_y_col'] = y_col

        chart_type = st.selectbox('Chart type:', ['Bar Chart', 'Line Chart', 'Pie Chart'], index=['Bar Chart', 'Line Chart', 'Pie Chart'].index(st.session_state['chart_type']), key='mongo_chart_type')
        if chart_type != st.session_state['chart_type']:
            st.session_state['chart_type'] = chart_type

        sort_order = st.selectbox('Sort order:', ['Descending', 'Ascending'], index=['Descending', 'Ascending'].index(st.session_state['chart_sort_order']), key='mongo_sort_order')
        if sort_order != st.session_state['chart_sort_order']:
            st.session_state['chart_sort_order'] = sort_order

        # Render the chart
        # Ensure y_col is valid before attempting to sort or plot
        if st.session_state['chart_x_col'] in data.columns and st.session_state['chart_y_col'] in data.columns:
            try:
                # Attempt to convert Y-axis to numeric for sorting and plotting if it's not already
                # This is important if Llama3 returns numbers as strings sometimes, or for sum/avg
                data_for_chart = data.copy()
                if not pd.api.types.is_numeric_dtype(data_for_chart[st.session_state['chart_y_col']]):
                    try:
                        data_for_chart[st.session_state['chart_y_col']] = pd.to_numeric(data_for_chart[st.session_state['chart_y_col']])
                    except ValueError:
                        st.warning(f"Could not convert Y-axis column '{st.session_state['chart_y_col']}' to numeric. Chart may not render correctly or sort as expected.")
                
                sorted_data = data_for_chart.sort_values(by=st.session_state['chart_y_col'], ascending=(st.session_state['chart_sort_order'] == 'Ascending'))
                
                title = f"{st.session_state['chart_y_col']} by {st.session_state['chart_x_col']}"
                if st.session_state['chart_type'] == 'Bar Chart':
                    fig = px.bar(sorted_data, x=st.session_state['chart_x_col'], y=st.session_state['chart_y_col'], color=st.session_state['chart_x_col'], title=title, text_auto=True)
                    fig.update_traces(textposition='outside')
                elif st.session_state['chart_type'] == 'Line Chart':
                    fig = px.line(sorted_data, x=st.session_state['chart_x_col'], y=st.session_state['chart_y_col'], markers=True, title=title, text=st.session_state['chart_y_col'])
                    fig.update_traces(textposition='top center')
                elif st.session_state['chart_type'] == 'Pie Chart':
                    fig = px.pie(sorted_data, names=st.session_state['chart_x_col'], values=st.session_state['chart_y_col'], title=title, hole=0.3)
                    fig.update_traces(textinfo='percent+label+value')
                
                if fig:
                    fig.update_layout(clickmode='event+select')
                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error rendering chart: {e}. Please check column selections and data types.")
        else:
            st.warning("Please select valid X and Y axis columns for the chart.")
            
        # Data table at the bottom
        st.dataframe(data, use_container_width=True, height=400)
    elif (run_prompt and question.strip()) or (run_suggested and selected_suggestion.strip()):
        # If a query was run but data is empty, this message is already shown by the spinner block.
        # This 'elif' can be used if we want a more generic "No data to display" if 'last_data' is empty
        # without necessarily having just run a query.
        # For now, it's covered.
        pass