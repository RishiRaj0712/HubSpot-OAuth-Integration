# hubspot.py

import json
import secrets
import hashlib
import base64
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from integrations.integration_item import IntegrationItem


CLIENT_ID = '96c8db26-2884-44e6-a2ff-3364d8ae92e6' 
CLIENT_SECRET = '7fb0f83a-5a93-4291-ab10-436a11ccf31c'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
AUTHORIZATION_URL = (
    f"https://app.hubspot.com/oauth/authorize"
    f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    f"&scope=crm.objects.contacts.read%20crm.objects.contacts.write%20crm.objects.companies.read%20crm.objects.companies.write%20crm.objects.deals.read%20crm.objects.deals.write%20oauth"
)

encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f"{AUTHORIZATION_URL}&state={encoded_state}"

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state or json.loads(saved_state).get('state') != state_data.get('state'):
        raise HTTPException(status_code=400, detail='State mismatch.')

    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.hubapi.com/oauth/v1/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'code': code,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail='Failed to retrieve access token.')

    credentials = response.json()
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(credentials), expire=3600)

    return HTMLResponse(content="<script>window.close();</script>")

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    return json.loads(credentials)

async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    access_token = credentials.get('access_token')
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    integration_items = []

    # Fetch Contacts
    contacts_url = 'https://api.hubapi.com/crm/v3/objects/contacts'
    async with httpx.AsyncClient() as client:
        contacts_response = await client.get(contacts_url, headers=headers)

    if contacts_response.status_code == 200:
        contacts = contacts_response.json().get('results', [])
        for contact in contacts:
            item = IntegrationItem(
                id=contact.get('id'),
                name=f"{contact.get('properties', {}).get('firstname', '')} {contact.get('properties', {}).get('lastname', '')}",
                type='Contact',
                creation_time=contact.get('createdAt'),
                last_modified_time=contact.get('updatedAt'),
                parent_id=None,
                visibility=True
            )
            integration_items.append(item)

    # Fetch Companies
    companies_url = 'https://api.hubapi.com/crm/v3/objects/companies'
    async with httpx.AsyncClient() as client:
        companies_response = await client.get(companies_url, headers=headers)

    if companies_response.status_code == 200:
        companies = companies_response.json().get('results', [])
        for company in companies:
            item = IntegrationItem(
                id=company.get('id'),
                name=company.get('properties', {}).get('name', 'Unnamed Company'),
                type='Company',
                creation_time=company.get('createdAt'),
                last_modified_time=company.get('updatedAt'),
                parent_id=None,
                visibility=True
            )
            integration_items.append(item)

    # Fetch Deals
    deals_url = 'https://api.hubapi.com/crm/v3/objects/deals'
    async with httpx.AsyncClient() as client:
        deals_response = await client.get(deals_url, headers=headers)

    if deals_response.status_code == 200:
        deals = deals_response.json().get('results', [])
        for deal in deals:
            item = IntegrationItem(
                id=deal.get('id'),
                name=deal.get('properties', {}).get('dealname', 'Unnamed Deal'),
                type='Deal',
                creation_time=deal.get('createdAt'),
                last_modified_time=deal.get('updatedAt'),
                parent_id=None,
                visibility=True
            )
            integration_items.append(item)

    return integration_items
