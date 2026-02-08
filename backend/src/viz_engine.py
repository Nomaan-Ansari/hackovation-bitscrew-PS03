import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from src.database_manager import get_conn

def get_fulfillment_chart():
    """Bar chart showing item fulfillment across all buckets."""
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT item_name, SUM(qty_total) as Total, SUM(qty_fulfilled) as Got 
        FROM payment_to_be_received_inv 
        GROUP BY item_name
    """, conn)
    conn.close()

    if df.empty: return None

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['item_name'], y=df['Total'], name='Requested', marker_color='gray'))
    fig.add_trace(go.Bar(x=df['item_name'], y=df['Got'], name='Fulfilled', marker_color='#00ff00'))
    fig.update_layout(barmode='group', title="Item Fulfillment Tracker", template="plotly_dark")
    return fig

def get_merit_trend_chart():
    """Line chart showing the history of merit changes."""
    conn = get_conn()
    query = """
        SELECT e.name, t.change, t.timestamp 
        FROM merit_audit_trail t 
        JOIN entity_master e ON t.entity_id = e.id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty: return None
    
    # Calculate cumulative merit over time for each entity
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df['cumulative_merit'] = df.groupby('name')['change'].cumsum() + 100

    fig = px.line(df, x='timestamp', y='cumulative_merit', color='name', 
                  title="Entity Reputation Trend", template="plotly_dark")
    return fig

def get_debt_exposure_chart():
    """Pie chart showing where most 'Incomplete' money is tied up."""
    conn = get_conn()
    # Logic: (Total - Fulfilled) * Price = Outstanding Debt
    df = pd.read_sql_query("""
        SELECT item_name, (qty_total - qty_fulfilled) * unit_price as Exposure 
        FROM payment_to_be_received_inv WHERE status != 'Completed'
    """, conn)
    conn.close()

    if df.empty: return None

    fig = px.pie(df, values='Exposure', names='item_name', hole=0.4,
                 title="Outstanding Debt Exposure", template="plotly_dark")
    return fig