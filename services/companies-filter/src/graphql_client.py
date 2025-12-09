import requests
import os
import logging

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")

def graphql(query, variables=None):
    response = requests.post(
        USERS_SERVICE_URL,
        json={"query": query, "variables": variables}
    )
    logging.info(f"Users response: {response.text}")
    return response.json()["data"]

def get_user(user_id):
    q = """
    query($id: String!) {
      user(id: $id) {
        id
        email
        phoneNumber
        region
        alerts
        role
      }
    }
    """
    return graphql(q, {"id": user_id})["user"]

def get_users_by_company_alert(company, region, level):
    q = """
    query($company: String!, $region: String!, $level: String!) {
      usersByCompanyAlert(company: $company, region: $region, level: $level) {
        id
        email
      }
    }
    """
    return graphql(q, {
        "company": company,
        "region": region,
        "level": level
    })["usersByCompanyAlert"]


def get_user_by_email(email):
    q = """
    query($email: String!) {
      userByEmail(email: $email) {
        id
        email
        phoneNumber
        region
        alerts
        role
      }
    }
    """
    return graphql(q, {"email": email})["userByEmail"]