import streamlit as st
import pandas as pd
from src.agents import run_query_agentic

# Page Config
st.set_page_config(page_title="QueryMate", layout="wide")

st.title("🤖 QueryMate: Agentic SQL Assistant")
st.markdown("Ask questions about your **Employees**, **Departments**, or **Projects**.")

# Sidebar for Sample Questions
with st.sidebar:
    st.header("Try these:")
    st.code("Who is the manager of the IT department?")
    st.code("Show me employees earning more than 80000")
    st.code("List projects with 'Pending' status")

# Main Input
question = st.text_input("Enter your question:", placeholder="e.g., How many employees in Sales?")

if st.button("Run Analysis"):
    if question:
        with st.spinner("Agents are collaborating..."):
            result = run_query_agentic(question)
        
        # Display Logs (The "Transparency" feature)
        with st.expander("See Agent Thought Process"):
            for log in result["logs"]:
                st.markdown(log)

        # Display Results
        if result["status"] == "success":
            st.success("Query Executed Successfully!")
            
            # Show the Final SQL
            st.code(result["sql"], language="sql")
            
            # Show Data
            if result["data"]:
                df = pd.DataFrame(result["data"], columns=result["headers"])
                st.dataframe(df)
            else:
                st.warning("Query ran successfully but returned no data.")
        else:
            st.error(f"Analysis Failed: {result['error']}")
    else:
        st.warning("Please enter a question first.")