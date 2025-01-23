import streamlit as st
import requests
import pandas as pd
import sqlite3
import plotly.graph_objects as go

st.set_page_config(page_title="Customer Analytics Platform", layout="wide")

page = st.sidebar.selectbox("☰  Menu ", ["Segmentation RFM", "Dashboard Customer Experience"])

st.markdown("""
    <style>
    /* Page Background */
    body {
        background-color: #f3f3f3;
        color: #333;
    }

    /* Custom Boxes */
    .box {
        background-color: #e8e8e8;
        border: 2px solid #b3b3b3;
        border-radius: 12px;
        padding: 20px;
        margin: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .box:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
    }

    /* Highlighted Metrics */
    .highlight {
        color: #d80027; /* Red tone */
        font-weight: bold;
    }

    /* Section Headers */
    .section-title {
        font-size: 1.5em;
        color: #b30000; /* Dark red */
        border-bottom: 2px solid #d80027;
        margin-bottom: 15px;
    }

    /* Title with Animation */
    .title {
        text-align: center;
        color: grey;
        animation: fade-in 4s ease-in-out;
    }
    @keyframes fade-in {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }
    </style>
    <h1 class='title'> PROJET: DATA SCIENCE 2  </h1>
""", unsafe_allow_html=True)


# SQL
def connect_and_fetch(database_path, query):
    """Fetches data from SQLite database."""
    connection = sqlite3.connect(database_path)
    data = pd.read_sql(query, connection)
    connection.close()
    return data


# Page: RFM Segmentation Platform
if page == "Segmentation RFM":
    st.title("📊 Segmentation RFM")

    API_BASE_URL = "http://127.0.0.1:8000"
    api_status = requests.get(f"{API_BASE_URL}/health")

    # Section: Client List
    st.markdown('<div class="section-title">👥 Client List</div>', unsafe_allow_html=True)
    clients_rep = requests.get(f"{API_BASE_URL}/clients")
    if clients_rep.status_code == 200:
        clients = clients_rep.json()
        client_ids = [client['customer_id'] for client in clients]

        col1, col2 = st.columns([2, 3])
        with col1:
            client_sel = st.selectbox("Selection un Client:", client_ids)

        if client_sel:
            details_clients = requests.get(f"{API_BASE_URL}/client/{client_sel}")
            if details_clients.status_code == 200:
                client_details = details_clients.json()

                # Informations Client 
                st.markdown("""
                    <div class="box">
                        <h3>📝 Informations Client </h3>
                        <p><strong>ID:</strong> {}</p>
                        <p><strong>Cluster:</strong> <span class="highlight">{}</span></p>
                        <p><strong>Type:</strong> {}</p>
                    </div>
                    <div class="box">
                        <h3>💰 RFM Scores</h3>
                        <p><strong>Recence:</strong> {} days</p>
                        <p><strong>Frequence:</strong> {} orders</p>
                        <p><strong>Monetaire:</strong> €{}</p>
                        <p><strong>Satisfaction:</strong> ⭐{}</p>
                    </div>
                """.format(
                    client_details['customer_id'],
                    client_details['Cluster'],
                    client_details['type'],
                    client_details['recency'],
                    client_details['frequency'],
                    client_details['monetary'],
                    client_details['satisfaction']
                ), unsafe_allow_html=True)

                # Gauge
                score_client_dormant = 80 if client_details['Cluster'] == 1 else 20
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=score_client_dormant,
                    title={'text': "Probabilité des clients dormants", 'font': {'size': 20}},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': '#d80027' if score_client_dormant > 50 else 'lightgreen'},
                        'steps': [
                            {'range': [0, 50], 'color': "#d0e8d0"},
                            {'range': [50, 75], 'color': "#ffc285"},
                            {'range': [75, 100], 'color': "#ff6666"}
                        ]
                    }
                ))
                st.plotly_chart(fig)

    st.markdown('<div class="section-title">Les Meilleurs et les Pires Clients </div>', unsafe_allow_html=True)
    les_meilleures = requests.get(f"{API_BASE_URL}/top-clients")
    if les_meilleures.status_code == 200:
        top_clients = pd.DataFrame(les_meilleures.json())
        st.markdown("### 👍 Les Meilleurs Clients")
        st.dataframe(top_clients.style.set_properties(**{'background-color': '#d0e8d0'}), use_container_width=True)

    les_pires = requests.get(f"{API_BASE_URL}/worst-clients")
    if les_pires.status_code == 200:
        pires_clients = pd.DataFrame(les_pires.json())
        st.markdown("###  👎 Pires Clients")
        st.dataframe(pires_clients.style.set_properties(**{'background-color': '#ffe5e5'}), use_container_width=True)

# Page: Dashboard Customer Experience
else:
    st.title("Dashboard Customer Experience")

    # Database path
    database_path = "olist.db"

    # --- Requête 1 : Commandes récentes avec retard ---
    query1 = """
    SELECT order_id, 
           customer_id, 
           order_status, 
           order_purchase_timestamp, 
           order_delivered_customer_date,
           order_estimated_delivery_date
    FROM orders 
    WHERE order_status != 'canceled'
      AND order_purchase_timestamp >= (
          SELECT DATE(MAX(order_purchase_timestamp), '-3 MONTHS')
          FROM orders
      )
      AND order_delivered_customer_date > DATE(order_estimated_delivery_date, '+3 DAYS')
    ORDER BY order_purchase_timestamp DESC;
    """
    commandes_retard = connect_and_fetch(database_path, query1)
    total_commandes_retard = len(commandes_retard)

    # --- Requête 2 : Vendeurs générant un CA > 100,000 Real ---
    query2 = """
    SELECT 
        s.seller_id, 
        SUM(oi.price + oi.freight_value) AS total_revenue
    FROM 
        order_items oi
    JOIN 
        sellers s ON oi.seller_id = s.seller_id
    JOIN 
        orders o ON oi.order_id = o.order_id
    WHERE 
        o.order_status = 'delivered'
    GROUP BY 
        s.seller_id
    HAVING 
        total_revenue > 100000
    ORDER BY 
        total_revenue DESC;
    """
    top_sellers = connect_and_fetch(database_path, query2)
    total_top_sellers = len(top_sellers)

    # --- Requête 3 : Codes postaux avec les pires scores moyens de review ---
    query3 = """
    SELECT 
        c.customer_zip_code_prefix, 
        AVG(orv.review_score) AS avg_review_score, 
        COUNT(orv.review_id) AS review_count
    FROM 
        order_reviews orv
    JOIN 
        orders o ON o.order_id = orv.order_id
    JOIN 
        customers c ON c.customer_id = o.customer_id
    WHERE 
        DATE(orv.review_creation_date) > (
            SELECT DATE(MAX(review_creation_date), '-12 months') 
            FROM order_reviews
        )
    GROUP BY 
        c.customer_zip_code_prefix
    HAVING 
        review_count > 30
        AND avg_review_score <= 3.7
    ORDER BY 
        avg_review_score ASC
    LIMIT 5;
    """
    worst_zip_codes = connect_and_fetch(database_path, query3)
    total_worst_zip_codes = len(worst_zip_codes)

    # --- Requête 4 : Analyse RFM des Clients ---
    query5 = """
    SELECT 
        o.customer_id,
        CAST(JULIANDAY('now') - JULIANDAY(MAX(o.order_purchase_timestamp)) AS INTEGER) AS recency,
        COUNT(o.order_id) AS frequency,
        SUM(oi.price) AS monetary
    FROM 
        orders o
    JOIN 
        order_items oi ON o.order_id = oi.order_id
    WHERE 
        o.order_status = 'delivered'
    GROUP BY 
        o.customer_id;
    """
    rfm_clients = connect_and_fetch(database_path, query5)
    total_clients_rfm = len(rfm_clients)

    # --- Affichage des KPIs ---
    st.markdown("### 📊 Résumé des KPIs")
    col1, col2, col3 = st.columns(3)

    col1.metric("Commandes en retard", total_commandes_retard)
    col2.metric("Vendeurs > 100k Real", total_top_sellers)
    col3.metric("Pires codes postaux", total_worst_zip_codes)

    # --- Section des tableaux interactifs ---
    st.subheader("📦 Détails des Commandes Récentes avec Retard")
    st.dataframe(commandes_retard, use_container_width=True)

    st.subheader("🏆 Détails des Vendeurs avec CA > 100,000 Real")
    st.dataframe(top_sellers, use_container_width=True)

    st.subheader("🏠 Codes Postaux avec les Pires Scores Moyens")
    st.dataframe(worst_zip_codes, use_container_width=True)

    st.subheader("🔍 Analyse RFM des Clients")
    st.dataframe(rfm_clients, use_container_width=True)