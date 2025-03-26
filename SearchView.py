import streamlit as st
import pandas as pd
from collections import defaultdict
import os

# Set page configuration
st.set_page_config(
    page_title="View Dependency Explorer", 
    page_icon="🔍", 
    layout="wide"
)

def load_view_dependencies(file_path='viewDependencies.csv'):
    """
    Load view dependencies from a CSV file.
    
    Args:
        file_path (str): Path to the CSV file with view dependencies
    
    Returns:
        pandas.DataFrame: DataFrame with view dependencies
    """
    # Read the CSV file with specific column names
    df = pd.read_csv(file_path, delimiter='|', 
                     names=['ViewName', 'ReferencedTable', 'ReferencedColumns'],
                     dtype=str)  # Explicitly convert to string type
    
    # Fill NaN values with empty string
    df = df.fillna('')
    
    return df

def load_view_columns(file_path='viewColumns.csv'):
    """
    Load view output columns from a CSV file.
    
    Args:
        file_path (str): Path to the CSV file with view dependencies
    
    Returns:
        pandas.DataFrame: DataFrame with view output columns
    """
    # Read the CSV file with specific column names
    df = pd.read_csv(file_path, delimiter='|', 
                     names=['ViewName', 'OutputColumns'],
                     dtype=str)  # Explicitly convert to string type
    
    # Fill NaN values with empty string
    df = df.fillna('')
    
    return df

def search_view_dependencies(df, search_terms, view_cols, view_code):
    """
    Search view dependencies based on user input terms.
    
    Args:
        df (pandas.DataFrame): View dependencies DataFrame
        search_terms (str): Comma or space-separated search terms
        view_cols (pandas.DataFrame): DataFrame with view output columns
        view_code (list): List of view names and their corresponding code
    
    Returns:
        list: Matched views with all their dependencies and code
    
    Search Logic:
    1. If a term starts with '>', search the term in the output columns with substring match.
       Example: '>Name' will find any view with any output column containing the substring "name" (case insensitive).
    2. If a term contains '%', perform substring match:
       - 'Client.%name' matches table name 'client' (exact match) and any dependent column containing the substring "name".
       - '%.%Name' matches any dependent table with any dependent column containing the substring 'name'.
    3. If no '>' or '%' in the term, use the current logic:
       - 'Table.Column' matches views referencing the specific table and column.
       - 'Table' matches views referencing the table.
    """
    # Parse search terms, handling both comma and space separators
    terms = [term.strip() for term in search_terms.replace(',', ' ').split()]
    
    # Add ',' before and after the column list for exact match
    df['ReferencedColumns'] = ',' + df['ReferencedColumns'] + ','
    
    # Initialize matched views with all views
    matched_views = set(df['ViewName'])
    
    # Find matched views based on search terms
    for term in terms:
        if term.startswith('>'): # Search in output columns with substring match
            search_term = term[1:].strip().lower()
            matches = set(view_cols[view_cols['OutputColumns'].str.contains(search_term, case=False, na=False)]['ViewName'])
        else: # search in referenced tables and columns
            parts = term.split('.')
            table = parts[0].strip().lower()
            column = ''
            if len(parts) > 1: 
                column = parts[1].strip().lower()
            
            if table.startswith('%'):
                table = table[1:]
            else:
                table = ',' + table + ','
            
            if column.startswith('%'):
                column = column[1:]
            elif len(column) > 0:
                column = ',' + column + ','
            
            matches = set(df[(
                ((',' + df['ReferencedTable'] + ',').str.contains(table, case=False, na=False)) & 
                ((',' + df['ReferencedColumns'] + ',').str.contains(column, case=False, na=False))
            )]['ViewName'])
        
        # Intersect with the current matched views
        matched_views.intersection_update(matches)

    # Prepare result with all dependencies for matched views
    result = []
    for view in sorted(matched_views):
        # Get all dependencies for this view
        view_dependencies = df[df['ViewName'] == view]
        
        # Get output columns for this view
        output_columns = view_cols[view_cols['ViewName'] == view]['OutputColumns'].values
        output_columns = output_columns[0] if len(output_columns) > 0 else ''
        
        # Get code for this view
        code = next((code for name, code in view_code if name == view), '')
        
        # Create a list of dependencies
        dependencies = [
            {
                'Table': row['ReferencedTable'], 
                'Columns': row['ReferencedColumns'].strip(',')
            } 
            for _, row in view_dependencies.iterrows()
        ]
        
        # Create an entry for this view
        result.append({
            'View': view,
            'Dependencies': dependencies,
            'OutputColumns': output_columns,
            'Code': code
        })
    
    return result

def GetCode():
    with open('ALL_views.txt', 'r', encoding='utf-8') as f:
        file_content = f.read()
    obj_raw = file_content.split('|||')
    objs = []
    for item in obj_raw:
        if '^^^' in item.strip():  # Ensure it contains valid data
            name, code = item.split('^^^', 1)
            objs.append([name.strip(), code.strip()])
    return objs

def display_results(result):
    """
    Display the search results using Streamlit components
    
    Args:
        result (list): List of dictionaries with view and dependencies
    """
    # Display the count of matched views
    st.markdown("### Search Results")
    st.markdown(f"#### {len(result)} views matched")
    
    for item in result:
        # Bold for matched view
        st.markdown("========================================================================================")
        st.markdown(f"### {item['View']}")
        st.markdown("========================================================================================")
        
        # Add output columns
        if item['OutputColumns']:
            with st.expander("Output Columns"):
                st.markdown(item['OutputColumns'])
        
        with st.expander("Dependencies"):
            for dep in item['Dependencies']:
                # Bold for dependent table and same line for columns
                columns = dep['Columns'].split(',')
                formatted_columns = ", ".join([f"*{col.strip()}*" for col in columns])
                st.markdown(f"**[{dep['Table']}]**: {formatted_columns}")
        
        # Add code expander
        if item['Code']:
            with st.expander("Code"):
                st.code(item['Code'], language='sql')
        
        st.markdown("")  # Add blank line between views

def main():
    """
    Streamlit app for view dependency search
    """
    # Simple login control
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if username != "kensingtontours" or password != "itsp-inc":
        st.sidebar.error("Invalid username or password")
        return

    view_deps = load_view_dependencies()
    view_cols = load_view_columns()
    view_Code = GetCode()
    
    # App title and description
    st.title("View Dependency Search")
    st.markdown("""
    #### Search Database View Dependencies
    
    Enter search terms to find views based on:
    - Tables (e.g., 'Booking')
    - Specific table columns (e.g., 'Itinerary.ItineraryId')
    - Multiple search terms supported
    
    #### Search Examples:
    - `Booking`
    - `Itinerary.ItineraryId`
    - `Booking Itinerary.Name`
    """)
    
    # Search input
    search_input = st.text_input(
        "Enter Search Terms", 
        placeholder="Booking Itinerary.ItineraryId"
    )
    
    # Perform search when search terms are provided
    if search_input:
        try:
            # Load the CSV file
            
            # Perform search
            results = search_view_dependencies(view_deps, search_input, view_cols, view_Code)
            
            # Display results
            if results:
                display_results(results)
            else:
                st.warning("No matching views found.")
        
        except Exception as e:
            st.error(f"An error occurred: {e}")

# Run the Streamlit app
if __name__ == "__main__":
    main()