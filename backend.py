from fastapi import FastAPI, HTTPException
import sqlite3
import pandas as pd
import joblib

# Chemin vers la base de données
DB_PATH = "olist.db"

# Charger le modèle et le scaler
kmeans = joblib.load('kmeans_model.pkl')
scaler = joblib.load('scaler.pkl')

# Créer l'application FastAPI
app = FastAPI()

@app.get("/health")
def health_check():
    """Vérifie si l'API fonctionne correctement."""
    return {"status": "API is running"}

@app.get("/clients")
def get_clients():
    """
    Retourne une liste simplifiée des clients :
    - customer_id
    """
    try:
        # Connexion à la base SQLite
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT DISTINCT customer_id FROM orders;"
        clients = pd.read_sql(query, conn)
        conn.close()

        return clients.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{customer_id}")
def get_client_details(customer_id: str):
    """
    Retourne les détails d’un client :
    - Récence, Fréquence, Montant, Satisfaction.
    - Segment (Cluster).
    """
    try:
        # Connexion à la base SQLite
        conn = sqlite3.connect(DB_PATH)

        # Récupérer les scores RFM et satisfaction
        query = f"""
        SELECT 
            o.customer_id,
            CAST((JULIANDAY((SELECT MAX(order_purchase_timestamp) FROM orders)) 
                  - JULIANDAY(MAX(o.order_purchase_timestamp))) AS INTEGER) AS recency,
            COUNT(o.order_id) AS frequency,
            SUM(oi.price) AS monetary,
            AVG(orw.review_score) AS satisfaction
        FROM 
            orders o
        JOIN 
            order_items oi ON o.order_id = oi.order_id
        LEFT JOIN 
            order_reviews orw ON o.order_id = orw.order_id
        WHERE 
            o.customer_id = '{customer_id}'
        GROUP BY 
            o.customer_id;
        """
        client_data = pd.read_sql(query, conn)
        conn.close()

        if client_data.empty:
            raise HTTPException(status_code=404, detail="Client not found")

        # Préparer les données pour la prédiction du cluster
        client = client_data.iloc[0].to_dict()
        input_data = [[
            client['recency'],
            client['frequency'],
            client['monetary'],
            client['satisfaction']
        ]]
        scaled_data = scaler.transform(input_data)
        cluster = kmeans.predict(scaled_data)[0]

        # Ajouter le cluster et le type de client
        client['Cluster'] = int(cluster)
        if cluster == 0:
            client['type'] = "Clients Perdus"
        elif cluster == 1:
            client['type'] = "Clients Dormants Satisfaits"
        elif cluster == 2:
            client['type'] = "Clients Perdus Satisfaits"
        elif cluster == 3:
            client['type'] = "Clients à Forte Valeur"
        else:
            client['type'] = "Inconnu"




        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/top-clients")
def get_top_clients():
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT 
            o.customer_id,
            CAST((JULIANDAY((SELECT MAX(order_purchase_timestamp) FROM orders)) 
                  - JULIANDAY(MAX(o.order_purchase_timestamp))) AS INTEGER) AS recency,
            COUNT(o.order_id) AS frequency,
            SUM(oi.price) AS monetary,
            AVG(orw.review_score) AS satisfaction
        FROM 
            orders o
        JOIN 
            order_items oi ON o.order_id = oi.order_id
        LEFT JOIN 
            order_reviews orw ON o.order_id = orw.order_id
        GROUP BY 
            o.customer_id
        ORDER BY 
            monetary DESC
        LIMIT 5;
        """
        top_clients = pd.read_sql(query, conn)
        conn.close()

        # Nettoyer les données
        top_clients = top_clients.fillna(0)
        top_clients = top_clients.replace([float('inf'), float('-inf')], 0)

        return top_clients.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/worst-clients")
def get_worst_clients():
    """
    Retourne les 5 pires clients :
    - Basé sur le montant dépensé (monetary).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT 
            o.customer_id,
            CAST((JULIANDAY((SELECT MAX(order_purchase_timestamp) FROM orders)) 
                  - JULIANDAY(MAX(o.order_purchase_timestamp))) AS INTEGER) AS recency,
            COUNT(o.order_id) AS frequency,
            SUM(oi.price) AS monetary,
            AVG(orw.review_score) AS satisfaction
        FROM 
            orders o
        JOIN 
            order_items oi ON o.order_id = oi.order_id
        LEFT JOIN 
            order_reviews orw ON o.order_id = orw.order_id
        GROUP BY 
            o.customer_id
        ORDER BY 
            monetary ASC
        LIMIT 5;
        """
        worst_clients = pd.read_sql(query, conn)
        conn.close()

        return worst_clients.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))