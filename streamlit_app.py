import streamlit as st
import os
import sys
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
import re

from src.components.sidebar import render_sidebar
from src.components.output_handler import capture_output
from src.lead_generator.crew import LeadGenerator
from src.utils.pricing import ModelsPricing

# Set page configuration
st.set_page_config(
    page_title="Lead Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header with centered title
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Center the main title using markdown with HTML
    st.markdown("<h1 style='text-align: center;'>🔍 Lead Generator AI Crew</h1>", unsafe_allow_html=True)

# Render sidebar and get user configuration
config = render_sidebar()

# Create 3 columns with the middle one being wider
left_col, center_col, right_col = st.columns([1, 2, 1])

# Use the center column for all our content
with center_col:
    # First section: "Start Your Research" (now centered)
    st.markdown("<h2 style='text-align: center;'>Start Your Research</h2>", unsafe_allow_html=True)
    
    # Market research topic input - connected to session state
    if 'topic' not in st.session_state:
        st.session_state.topic = ""
        
    industry = st.text_input(
        "Enter a industry to research",
        placeholder="e.g., AI LLMs, Renewable Energy, FinTech",
        help="Specify the industry you want to explore for potential leads",
        key="industry"  # This links the input to st.session_state.industry
    )
    
    country = st.text_input(
        "Enter a country to research",
        placeholder="e.g., United States, United Kingdom, Canada",
        help="Specify the country you want to explore for potential leads",
        key="country"  # This links the input to st.session_state.country
    )

    # Example topics that users can click
    st.write("Or try one of these examples:")
    example_col1, example_col2, example_col3 = st.columns(3)
    
    # Define example topics
    examples = [
        "AI-powered SaaS platforms",
        "Renewable Energy Startups",
        "FinTech Payment Solutions"
    ]
    
    # Define click handler function
    def set_example_topic(example):
        st.session_state.industry = example  # Update industry instead of topic
        
    # Add a button for each example
    with example_col1:
        st.button(examples[0], on_click=set_example_topic, args=(examples[0],), key="example1")
        
    with example_col2:
        st.button(examples[1], on_click=set_example_topic, args=(examples[1],), key="example2")
        
    with example_col3:
        st.button(examples[2], on_click=set_example_topic, args=(examples[2],), key="example3")
    
    # Generate button
    run_button = st.button("🚀 Generate Leads", type="primary", use_container_width=True)
    
    # Add a small space
    st.write("")
    
    # Second section: "Why Use AI-Powered Lead Generation?" in expandable block
    with st.expander("Why Use AI-Powered Lead Generation?"):
        st.subheader("⚡ Speed & Efficiency")
        st.write("Generate leads 10x faster than manual methods")
        
        st.subheader("🎯 Precision Targeting")
        st.write("Identify prospects that match your ideal customer profile")
        
        st.subheader("📊 Data-Driven Insights")
        st.write("Make informed decisions based on comprehensive research")

# Results area (initially hidden)
results_container = st.container()

# Initialize session state for persistent storage
if 'results' not in st.session_state:
    st.session_state.results = None
if 'pricing_tracker' not in st.session_state:
    st.session_state.pricing_tracker = ModelsPricing()

# Update the run button section to preserve state
if run_button:
    if not industry or not country:
        st.error("Please enter an industry and country")
    elif not os.environ.get("OPENAI_API_KEY"):
        st.warning("⚠️ Please enter your OpenAI API key in the sidebar to continue")
    else:
        with st.status("🤖 Researching... This may take several minutes.", expanded=True) as status:
            try:
                # Initialize the crew
                lead_gen_crew = LeadGenerator().crew()
                
                # Run the crew with industry and country inputs
                results = lead_gen_crew.kickoff(inputs={
                    "industry": industry,
                    "country": country
                })
                
                # Store results in session state immediately
                st.session_state.results = results
                status.update(label="✅ Lead generation completed!", state="complete", expanded=False)
                
                # Now let's process the results first
                with results_container:
                    st.success("✅ Lead generation process completed successfully!")
                    
                    st.markdown("### Your Leads are ready!")
                    
                    try:
                        # Get the results from the CrewOutput object
                        results = st.session_state.results
                        
                        # Try to get the last task's output
                        if hasattr(results, 'tasks_output') and results.tasks_output:
                            last_task = results.tasks_output[-1]
                            if hasattr(last_task, 'raw'):
                                results_list = json.loads(last_task.raw)
                            else:
                                # Fallback to raw attribute if it exists
                                results_list = json.loads(results.raw) if hasattr(results, 'raw') else []
                        else:
                            # If no tasks_output, try raw directly
                            results_list = json.loads(results.raw) if hasattr(results, 'raw') else []

                        if not results_list:
                            st.warning("No leads were found in the results")
                            st.stop()

                        # Create metrics summary
                        total_leads = len(results_list)
                        avg_score = sum(float(lead.get('score', 0)) for lead in results_list if isinstance(lead, dict)) / total_leads if total_leads > 0 else 0
                        
                        # Display metrics summary
                        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                        with metrics_col1:
                            st.metric("Total Leads", f"{total_leads}")
                        with metrics_col2:
                            st.metric("Average Score", f"{avg_score:.1f}/10")
                        with metrics_col3:
                            st.metric("High-Quality Leads", f"{sum(1 for lead in results_list if isinstance(lead, dict) and float(lead.get('score', 0)) >= 7)}")

                        # Sort leads by score (highest first)
                        results_list = sorted(
                            results_list,
                            key=lambda x: float(x.get('score', 0)) if isinstance(x, dict) else 0,
                            reverse=True
                        )

                        # Display each lead in a structured format
                        for idx, lead in enumerate(results_list, 1):
                            if not isinstance(lead, dict):
                                continue
                            
                            # Create an expander for each company
                            with st.expander(f"🏢 {idx}. {lead.get('company_name', 'Unknown Company')} (Score: {lead.get('score', 'N/A')}/10)", expanded=False):
                                # Company header with score-based color
                                score = float(lead.get('score', 0))
                                if score >= 8:
                                    header_color = "green"
                                elif score >= 6:
                                    header_color = "orange"
                                else:
                                    header_color = "gray"
                                
                                st.markdown(f"<h3 style='color: {header_color};'>{lead.get('company_name', 'N/A')}</h3>", unsafe_allow_html=True)
                                
                                col1, col2 = st.columns([3, 2])
                                
                                with col1:
                                    st.markdown("#### Company Information")
                                    st.markdown(f"**Annual Revenue:** {lead.get('annual_revenue', 'N/A')}")
                                    
                                    location = lead.get('location', {})
                                    if isinstance(location, dict):
                                        st.markdown(f"**Location:** {location.get('city', 'N/A')}, {location.get('country', 'N/A')}")
                                    else:
                                        st.markdown(f"**Location:** {location or 'N/A'}")
                                    
                                    website = lead.get('website_url', 'N/A')
                                    st.markdown(f"**Website:** [{website}]({website})" if website != 'N/A' else "**Website:** N/A")
                                    st.markdown(f"**Number of Employees:** {lead.get('num_employees', 'N/A')}")
                                
                                with col2:
                                    st.markdown("#### Company Profile")
                                    st.markdown(f"**Match Score:** {lead.get('score', 'N/A')}/10")
                                    st.progress(float(lead.get('score', 0)) / 10)
                                
                                st.markdown("#### Business Overview")
                                st.markdown(lead['review'] if 'review' in lead else 'N/A')
                                
                                if 'recommendations' in lead:
                                    st.markdown("#### Recommendations")
                                    st.markdown(lead['recommendations'])
                                
                                # Display key decision makers in markdown format
                                kdm = lead['key_decision_makers'] if 'key_decision_makers' in lead else []
                                if kdm:
                                    st.markdown("#### Key Decision Makers")
                                    for person in kdm:
                                        if isinstance(person, dict):
                                            name = person['name'] if 'name' in person else 'N/A'
                                            role = person['role'] if 'role' in person else 'N/A'
                                            linkedin = person['linkedin'] if 'linkedin' in person else '#'
                                            
                                            linkedin_link = f"[LinkedIn Profile]({linkedin})" if linkedin != '#' else 'N/A'
                                            st.markdown(f"**{name}** - {role} ({linkedin_link})")

                        # Add a JSON view option at the bottom
                        with st.expander("🔍 View Raw Data", expanded=False):
                            st.json(results_list)

                    except Exception as e:
                        st.error(f"Error displaying results: {str(e)}")
                        st.code(str(st.session_state.results), language='json')
                    
                    # Download section
                    st.markdown("### 📥 Download Research Report")
                    try:
                        # Prepare markdown report
                        download_data = "# Lead Generation Report\n\n"
                        for lead in results_list:
                            download_data += f"## {lead.get('company_name', 'N/A')}\n\n"
                            download_data += f"- **Annual Revenue:** {lead.get('annual_revenue', 'N/A')}\n"
                            download_data += f"- **Website:** {lead.get('website_url', 'N/A')}\n"
                            download_data += f"- **Review:** {lead.get('review', 'N/A')}\n"
                            download_data += f"- **Number of Employees:** {lead.get('num_employees', 'N/A')}\n"
                            download_data += f"- **Score:** {lead.get('score', 'N/A')}/10\n\n"
                            
                            # Add key decision makers
                            kdm = lead.get('key_decision_makers', [])
                            if kdm:
                                download_data += "### Key Decision Makers\n"
                                for person in kdm:
                                    if isinstance(person, dict):
                                        download_data += f"- {person.get('name', 'N/A')} ({person.get('role', 'N/A')}): {person.get('linkedin', 'N/A')}\n"
                                download_data += "\n"
                            
                            download_data += "---\n\n"
                        
                        # Also include raw JSON data at the end
                        download_data += "\n## Raw JSON Data\n\n```json\n"
                        download_data += json.dumps(results_list, indent=2)
                        download_data += "\n```\n"
                        
                    except Exception as e:
                        download_data = f"Error generating report: {str(e)}"
                    
                    st.download_button(
                        label="Download Full Report",
                        data=download_data,
                        file_name=f"lead_generation_report_{industry}_{country}.md",
                        mime="text/plain"
                    )

                    # Usage metrics section - immediately after results and download
                    st.markdown("### 💰 Usage Metrics")
                    
                    try:
                        # Check for usage metrics directly on the crew object (live, not from state)
                        if hasattr(lead_gen_crew, 'usage_metrics'):
                            metrics = lead_gen_crew.usage_metrics
                            
                            # First, let's display what we're dealing with for debugging
                            #st.write(f"Metrics type: {type(metrics)}")
                            metrics_str = str(metrics)
                            #st.write(f"Metrics value: {metrics_str}")
                            
                            # Parse the metrics - whether it's a string directly or a UsageMetrics object with string representation
                            metrics_dict = {}
                            parse_string = metrics_str
                            
                            # Split by space and extract key-value pairs
                            for item in parse_string.split():
                                if "=" in item:
                                    key, value = item.split("=")
                                    try:
                                        metrics_dict[key] = int(value)
                                    except ValueError:
                                        metrics_dict[key] = value
                            
                            # Display the parsed metrics
                            with st.expander("🔍 Parsed Metrics", expanded=False):
                                st.json(metrics_dict)
                            
                            # Extract relevant token counts
                            input_tokens = metrics_dict.get('prompt_tokens', 0)
                            output_tokens = metrics_dict.get('completion_tokens', 0)
                            total_tokens = metrics_dict.get('total_tokens', 0)
                            
                            # Calculate approximate cost based on gpt-4 rates
                            # $0.03/1K input tokens, $0.06/1K output tokens
                            input_cost = (input_tokens / 1000000) * 0.015
                            output_cost = (output_tokens / 1000000) * 0.06
                            total_cost = input_cost + output_cost
                            
                            # Update the pricing tracker
                            st.session_state.pricing_tracker.track_usage(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens
                            )
                            
                            # Display metrics in a user-friendly way
                            #st.success("Usage metrics processed successfully")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Cost", f"${total_cost:.4f}")
                            with col2:
                                st.metric("Input Tokens", f"{input_tokens:,}")
                            with col3:
                                st.metric("Output Tokens", f"{output_tokens:,}")
                            
                        # Try token_usage as fallback
                        elif hasattr(results, 'token_usage') and results.token_usage:
                            token_usage = results.token_usage
                            
                            # Display the token usage data
                            with st.expander("🔍 Token Usage Data", expanded=False):
                                st.write(token_usage)
                            
                            # Update the pricing tracker
                            if isinstance(token_usage, dict):
                                input_tokens = token_usage.get('total_prompt_tokens', 0)
                                output_tokens = token_usage.get('total_completion_tokens', 0)
                                
                                st.session_state.pricing_tracker.track_usage(
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens
                                )
                                
                                usage_summary = st.session_state.pricing_tracker.get_usage_summary()
                                
                                # Display metrics in a user-friendly way
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Cost", f"${usage_summary['total_cost']:.4f}")
                                with col2:
                                    st.metric("Input Tokens", f"{usage_summary['input_tokens']:,}")
                                with col3:
                                    st.metric("Output Tokens", f"{usage_summary['output_tokens']:,}")
                        else:
                            st.info("No usage metrics available for this run")
                            
                    except Exception as cost_error:
                        st.warning(f"Usage metrics calculation error: {str(cost_error)}")
                        st.warning("This doesn't affect your results, just the usage tracking.")
                        with st.expander("Error Details", expanded=False):
                            import traceback
                            st.code(traceback.format_exc())

            except Exception as e:
                status.update(label="❌ Error occurred", state="error")
                st.error(f"An error occurred: {str(e)}")
                st.stop()
                
# Remove the duplicate results handling code
if __name__ == "__main__":
    # This is only used when running the script directly
    pass

# Add footer
footer_col1, footer_col2, footer_col3 = st.columns([1, 2, 1])
with footer_col2:
    st.caption("Made with ❤️ using AI-powered lead generation technology")