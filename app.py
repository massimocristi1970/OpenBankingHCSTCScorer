"""
HCSTC Loan Scoring Application
Streamlit-based batch processing application for scoring consumer loan applications.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

from hcstc_batch_processor import HCSTCBatchProcessor, BatchResult
from scoring_engine import Decision
from config.categorization_patterns import PRODUCT_CONFIG


# Page configuration
st.set_page_config(
    page_title="HCSTC Loan Scorer",
    page_icon="💷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Initialize session state for cumulative batch processing
    if "cumulative_mode" not in st.session_state:
        st.session_state["cumulative_mode"] = False
    if "batch_count" not in st.session_state:
        st.session_state["batch_count"] = 0
    if "processed_filenames" not in st.session_state:
        st.session_state["processed_filenames"] = set()
    
    # Header
    st.markdown('<p class="main-header">💷 HCSTC Loan Scoring System</p>', unsafe_allow_html=True)
    st.markdown("**High-Cost Short-Term Credit** batch processing application for Open Banking data")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("Loan Parameters")
        
        loan_amount = st.number_input(
            "Requested Loan Amount (£)",
            min_value=PRODUCT_CONFIG["min_loan_amount"],
            max_value=PRODUCT_CONFIG["max_loan_amount"],
            value=500,
            step=50,
            help="Loan amount between £200 and £1,500"
        )
        
        loan_term = st.selectbox(
            "Loan Term (months)",
            options=PRODUCT_CONFIG["available_terms"],
            index=1,  # Default to 4 months
            help="Available terms: 3, 4, 5, or 6 months"
        )
        
        st.subheader("Data Parameters")
        
        months_of_data = st.slider(
            "Months of Transaction Data",
            min_value=1,
            max_value=12,
            value=3,
            help="Number of months of data in uploaded files"
        )
        
        st.divider()
        
        st.subheader("📋 Product Information")
        st.info(f"""
        **Loan Range**: £{PRODUCT_CONFIG['min_loan_amount']:,} - £{PRODUCT_CONFIG['max_loan_amount']:,}
        
        **Terms**: {', '.join(str(t) for t in PRODUCT_CONFIG['available_terms'])} months
        
        **Interest**: {PRODUCT_CONFIG['daily_interest_rate']*100}% per day
        
        **Total Cost Cap**: {PRODUCT_CONFIG['total_cost_cap']*100}%
        """)
        
        st.divider()
        
        st.markdown("### 📊 Score Ranges")
        st.markdown("""
        - **70-100**: APPROVE ✅
        - **50-69**: CONDITIONAL ⚠️
        - **30-49**: REFER 📋
        - **0-29**: DECLINE ❌
        """)
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "📊 Results Dashboard", "ℹ️ Help"])
    
    with tab1:
        render_upload_tab(loan_amount, loan_term, months_of_data)
    
    with tab2:
        render_results_tab()
    
    with tab3:
        render_help_tab()


def render_upload_tab(loan_amount: float, loan_term: int, months_of_data: int):
    """Render the upload and processing tab."""
    
    st.header("📤 Upload Application Files")
    
    st.markdown("""
    Upload JSON files or ZIP archives containing Open Banking transaction data in PLAID format.
    
    **Supported formats:**
    - Individual JSON files
    - ZIP archives containing multiple JSON files
    """)
    
    # Cumulative batch processing controls
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔄 Batch Processing Mode")
        cumulative_mode = st.checkbox(
            "**Add to Results** (Cumulative Mode)",
            value=st.session_state.get("cumulative_mode", False),
            help="When enabled, new results are added to existing results instead of replacing them. "
                 "Useful for processing large datasets in smaller batches."
        )
        st.session_state["cumulative_mode"] = cumulative_mode
        
        if cumulative_mode:
            st.info(
                "🔄 **Cumulative Mode Active** - New uploads will be added to existing results. "
                "Use 'Clear All Results' to start fresh."
            )
        else:
            st.info(
                "🔁 **Replace Mode Active** - New uploads will replace existing results."
            )
    
    with col2:
        st.subheader("🗑️ Clear Data")
        if st.button(
            "Clear All Results",
            type="secondary",
            use_container_width=True,
            help="Remove all accumulated results and start fresh"
        ):
            # Clear all session state data
            st.session_state["batch_result"] = None
            st.session_state["results_df"] = None
            st.session_state["errors_df"] = None
            st.session_state["batch_count"] = 0
            st.session_state["processed_filenames"] = set()
            st.success("✅ All results cleared!")
            st.rerun()
    
    # Show cumulative progress summary if in cumulative mode and results exist
    if cumulative_mode and "batch_result" in st.session_state and st.session_state["batch_result"] is not None:
        result = st.session_state["batch_result"]
        batch_count = st.session_state.get("batch_count", 0)
        
        st.subheader("📊 Cumulative Progress")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Batches Processed", batch_count)
        
        with col2:
            st.metric("Total Files", result.stats.total_files)
        
        with col3:
            st.metric("Total Successful", result.stats.successful)
        
        with col4:
            st.metric("Total Errors", result.stats.failed)
    
    st.divider()
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=["json", "zip"],
        accept_multiple_files=True,
        help="Upload JSON files or ZIP archives"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        
        # Show file list
        with st.expander("📁 Uploaded Files", expanded=False):
            for f in uploaded_files:
                file_size = f.size / 1024  # KB
                st.text(f"• {f.name} ({file_size:.1f} KB)")
        
        # Process button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            process_button = st.button(
                "🚀 Process Applications",
                type="primary",
                use_container_width=True
            )
        
        if process_button:
            process_applications(
                uploaded_files=uploaded_files,
                loan_amount=loan_amount,
                loan_term=loan_term,
                months_of_data=months_of_data
            )


def process_applications(
    uploaded_files: list,
    loan_amount: float,
    loan_term: int,
    months_of_data: int
):
    """Process uploaded applications."""
    
    # Initialize processor
    processor = HCSTCBatchProcessor(
        default_loan_amount=loan_amount,
        default_loan_term=loan_term,
        months_of_data=months_of_data
    )
    
    # Load files
    with st.spinner("Loading files..."):
        files = processor.load_files_from_uploads(uploaded_files)
    
    if not files:
        st.error("No valid JSON files found in uploads")
        return
    
    # Check for duplicate filenames if in cumulative mode
    cumulative_mode = st.session_state.get("cumulative_mode", False)
    processed_filenames = st.session_state.get("processed_filenames", set())
    
    if cumulative_mode and processed_filenames:
        filenames_to_process = {filename for filename, _ in files}
        duplicates = filenames_to_process & processed_filenames
        
        if duplicates:
            st.warning(
                f"⚠️ **Duplicate Files Detected**: {len(duplicates)} file(s) have already been processed:\n\n"
                f"{', '.join(list(duplicates)[:5])}" + 
                (f" and {len(duplicates) - 5} more..." if len(duplicates) > 5 else "") +
                f"\n\nYou can proceed to reprocess them or clear all results to start fresh."
            )
    
    # Determine batch number
    current_batch = st.session_state.get("batch_count", 0) + 1
    
    if cumulative_mode:
        st.info(f"📂 Processing Batch {current_batch}: {len(files)} application file(s)")
    else:
        st.info(f"📂 Found {len(files)} application file(s) to process")
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(current: int, total: int, message: str):
        progress = current / total
        progress_bar.progress(progress)
        if cumulative_mode:
            status_text.text(f"Batch {current_batch} [{current}/{total}] {message}")
        else:
            status_text.text(f"[{current}/{total}] {message}")
    
    # Process batch
    with st.spinner("Processing applications..."):
        new_result = processor.process_batch(
            files=files,
            loan_amount=loan_amount,
            loan_term=loan_term,
            progress_callback=update_progress
        )
    
    progress_bar.progress(1.0)
    status_text.text(f"✅ Processing complete: {new_result.stats.successful}/{new_result.stats.total_files} successful")
    
    # Handle cumulative mode
    if cumulative_mode and "batch_result" in st.session_state and st.session_state["batch_result"] is not None:
        # Merge with existing results
        existing_result = st.session_state["batch_result"]
        combined_result = BatchResult.merge_results(existing_result, new_result)
        
        # Update session state with merged results
        st.session_state["batch_result"] = combined_result
        st.session_state["results_df"] = processor.results_to_dataframe(combined_result.results)
        st.session_state["errors_df"] = processor.errors_to_dataframe(combined_result.errors)
        st.session_state["batch_count"] = current_batch
        
        # Update processed filenames
        for filename, _ in files:
            processed_filenames.add(filename)
        st.session_state["processed_filenames"] = processed_filenames
        
        # Show summary for both new batch and combined results
        st.subheader(f"📈 Batch {current_batch} Results")
        display_processing_summary(new_result)
        
        st.divider()
        
        st.subheader("📊 Combined Results (All Batches)")
        display_processing_summary(combined_result)
        
    else:
        # Not in cumulative mode or first batch - just store new results
        st.session_state["batch_result"] = new_result
        st.session_state["results_df"] = processor.results_to_dataframe(new_result.results)
        st.session_state["errors_df"] = processor.errors_to_dataframe(new_result.errors)
        st.session_state["batch_count"] = 1
        
        # Update processed filenames
        processed_filenames = set()
        for filename, _ in files:
            processed_filenames.add(filename)
        st.session_state["processed_filenames"] = processed_filenames
        
        # Show summary
        display_processing_summary(new_result)
    
    st.success("📊 View detailed results in the **Results Dashboard** tab")


def display_processing_summary(result: BatchResult):
    """Display processing summary."""
    
    st.subheader("📈 Processing Summary")
    
    stats = result.stats
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Files", stats.total_files)
    
    with col2:
        st.metric("Successful", stats.successful, delta=f"{stats.success_rate:.1f}%")
    
    with col3:
        st.metric("Failed", stats.failed, delta_color="inverse")
    
    with col4:
        st.metric("Average Score", f"{stats.average_score:.1f}")
    
    with col5:
        st.metric("Processing Time", f"{stats.processing_time:.1f}s")
    
    # Decision breakdown
    st.subheader("📊 Decision Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("✅ APPROVED", stats.approved)
    
    with col2:
        st.metric("⚠️ CONDITIONAL", stats.conditional)
    
    with col3:
        st.metric("📋 REFER", stats.referred)
    
    with col4:
        st.metric("❌ DECLINED", stats.declined)
    
    # Error summary
    if result.errors:
        with st.expander("⚠️ Error Summary", expanded=False):
            for error_type, count in result.error_summary.items():
                st.text(f"• {error_type}: {count}")


def render_results_tab():
    """Render the results dashboard tab."""
    
    st.header("📊 Results Dashboard")
    
    if "batch_result" not in st.session_state or st.session_state["batch_result"] is None:
        st.info("👆 Upload and process files in the **Upload & Process** tab first")
        return
    
    result = st.session_state["batch_result"]
    results_df = st.session_state.get("results_df")
    errors_df = st.session_state.get("errors_df")
    
    # Show cumulative mode indicator
    cumulative_mode = st.session_state.get("cumulative_mode", False)
    batch_count = st.session_state.get("batch_count", 0)
    
    if cumulative_mode and batch_count > 1:
        st.info(f"🔄 **Cumulative Mode**: Showing combined results from {batch_count} batches")
    
    if results_df is None or results_df.empty:
        st.warning("No successful results to display")
        return
    
    # Score Distribution
    st.subheader("📈 Score Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histogram
        fig_hist = px.histogram(
            results_df,
            x="Score",
            nbins=20,
            title="Score Distribution",
            color_discrete_sequence=["#1f77b4"]
        )
        fig_hist.add_vline(x=70, line_dash="dash", line_color="green", annotation_text="Approve")
        fig_hist.add_vline(x=50, line_dash="dash", line_color="orange", annotation_text="Conditional")
        fig_hist.add_vline(x=30, line_dash="dash", line_color="red", annotation_text="Refer")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Decision pie chart
        decision_counts = results_df["Decision"].value_counts()
        fig_pie = px.pie(
            values=decision_counts.values,
            names=decision_counts.index,
            title="Decision Distribution",
            color=decision_counts.index,
            color_discrete_map={
                "APPROVE": "#28a745",
                "APPROVE WITH CONDITIONS": "#ffc107",
                "REFER": "#17a2b8",
                "DECLINE": "#dc3545"
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Affordability Summary
    st.subheader("💰 Affordability Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Income vs Disposable scatter
        fig_scatter = px.scatter(
            results_df,
            x="Monthly Income",
            y="Monthly Disposable",
            color="Decision",
            title="Income vs Disposable Income",
            color_discrete_map={
                "APPROVE": "#28a745",
                "APPROVE WITH CONDITIONS": "#ffc107",
                "REFER": "#17a2b8",
                "DECLINE": "#dc3545"
            }
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        # Score breakdown box plot
        if "Affordability Score" in results_df.columns:
            score_breakdown_df = results_df[["Affordability Score", "Income Quality Score", 
                                             "Account Conduct Score", "Risk Indicators Score"]].melt(
                var_name="Component",
                value_name="Score"
            )
            fig_box = px.box(
                score_breakdown_df,
                x="Component",
                y="Score",
                title="Score Component Distribution"
            )
            st.plotly_chart(fig_box, use_container_width=True)
    
    # Risk Flags Summary
    st.subheader("⚠️ Risk Flags Summary")
    
    # Extract and count risk flags
    risk_flags = []
    for flags in results_df["Risk Flags"]:
        if flags:
            risk_flags.extend(flags.split("; "))
    
    if risk_flags:
        flag_counts = pd.Series(risk_flags).str.split(":").str[0].value_counts()
        fig_flags = px.bar(
            x=flag_counts.values,
            y=flag_counts.index,
            orientation="h",
            title="Risk Flag Frequency",
            labels={"x": "Count", "y": "Risk Flag"}
        )
        st.plotly_chart(fig_flags, use_container_width=True)
    else:
        st.info("No risk flags identified")
    
    # Detailed Results Table
    st.subheader("📋 Detailed Results")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        decision_filter = st.multiselect(
            "Filter by Decision",
            options=results_df["Decision"].unique(),
            default=results_df["Decision"].unique()
        )
    
    with col2:
        min_score = st.slider(
            "Minimum Score",
            min_value=0,
            max_value=100,
            value=0
        )
    
    with col3:
        risk_level_filter = st.multiselect(
            "Filter by Risk Level",
            options=results_df["Risk Level"].unique(),
            default=results_df["Risk Level"].unique()
        )
    
    # Apply filters
    filtered_df = results_df[
        (results_df["Decision"].isin(decision_filter)) &
        (results_df["Score"] >= min_score) &
        (results_df["Risk Level"].isin(risk_level_filter))
    ]
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Download buttons
    st.subheader("💾 Download Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_buffer = io.StringIO()
        results_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Results CSV",
            data=csv_buffer.getvalue(),
            file_name=f"hcstc_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        if not errors_df.empty:
            error_csv = io.StringIO()
            errors_df.to_csv(error_csv, index=False)
            st.download_button(
                label="📥 Download Errors CSV",
                data=error_csv.getvalue(),
                file_name=f"hcstc_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # Errors table
    if not errors_df.empty:
        st.subheader("❌ Processing Errors")
        st.dataframe(errors_df, use_container_width=True, hide_index=True)


def render_help_tab():
    """Render the help tab."""
    
    st.header("ℹ️ Help & Documentation")
    
    st.subheader("📁 JSON Data Format")
    
    st.markdown("""
    Files must be in PLAID format with the following structure:
    """)
    
    st.code('''
{
  "accounts": [
    {
      "account_id": "xxx",
      "name": "Current Account",
      "type": "depository",
      "subtype": "checking",
      "balances": {
        "available": 1234.56,
        "current": 1234.56,
        "iso_currency_code": "GBP"
      }
    }
  ],
  "transactions": [
    {
      "account_id": "xxx",
      "transaction_id": "xxx",
      "amount": 123.45,
      "date": "2024-01-15",
      "name": "TRANSACTION DESCRIPTION",
      "merchant_name": "Merchant Name",
      "personal_finance_category.detailed": "category_name"
    }
  ]
}
    ''', language="json")
    
    st.markdown("""
    **Amount Convention:**
    - **Negative amounts** = Credits (money in)
    - **Positive amounts** = Debits (money out)
    """)
    
    st.subheader("📊 Scoring System")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Score Components (100 points total):**
        
        1. **Affordability (45 points)**
           - Debt-to-Income Ratio: 18 pts
           - Disposable Income: 15 pts
           - Post-Loan Affordability: 12 pts
        
        2. **Income Quality (25 points)**
           - Income Stability: 12 pts
           - Income Regularity: 8 pts
           - Income Verification: 5 pts
        """)
    
    with col2:
        st.markdown("""
        3. **Account Conduct (20 points)**
           - Failed Payments: 8 pts
           - Overdraft Usage: 7 pts
           - Balance Management: 5 pts
        
        4. **Risk Indicators (10 points)**
           - Gambling Activity: 5 pts
           - HCSTC History: 5 pts
        """)
    
    st.subheader("🚫 Hard Decline Rules")
    
    st.markdown("""
    Applications are automatically declined if any of these conditions apply:
    
    - Monthly income < £500
    - No identifiable income source
    - Active HCSTC with 3+ lenders
    - Gambling > 15% of income
    - Post-loan disposable < £30
    - 5+ failed payments in period
    - Active debt collection (3+ DCAs)
    - DTI would exceed 60% with new loan
    """)
    
    st.subheader("💷 Loan Amount Determination")
    
    st.markdown("""
    The approved loan amount is the **lowest** of:
    
    1. **Product Maximum**: £1,500
    2. **Affordability Maximum**: Based on disposable income
    3. **Score-Based Maximum**:
       - Score 85-100: Up to £1,500, 6 months
       - Score 70-84: Up to £1,200, 6 months
       - Score 60-69: Up to £800, 5 months
       - Score 50-59: Up to £500, 4 months
       - Score 40-49: Up to £300, 3 months (refer)
    """)


if __name__ == "__main__":
    main()
