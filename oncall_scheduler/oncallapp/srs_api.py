import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup as soup
import os
import socket
from OpenSSL import SSL, crypto

# Get the root Certificate IntactRootCA.crt  Needed for Validating Every Request top of Cert Chain
hostname =  "srssipt.intact.net"
port = 443
CERT_NAME = "IntactRootCA.crt"

def get_cert_chain(hostname,port,cert_name=CERT_NAME):
    context = SSL.Context(SSL.TLS_CLIENT_METHOD)
    context.set_verify(SSL.VERIFY_NONE, lambda conn, cert, errno,depth,ok: ok)

    sock = socket.create_connection((hostname,port))
    connection = SSL.Connection(context,sock)
    connection.set_tlsext_host_name(hostname.encode())
    connection.set_connect_state()
    connection.do_handshake()

    chain = connection.get_peer_cert_chain()

    if chain:
        #Last Cert is root in chain usually
        root_cert = chain[-1]
        with open (f"{cert_name}",'w+') as cert_file:
            cert_file.write(crypto.dump_certificate(crypto.FILETYPE_PEM,root_cert).decode('utf-8'))
            print(f"Root {hostname} Cert Added To file {cert_name}", flush=True)
    connection.close()
    sock.close()


def get_root(override_hostname=None,override_port=None,override_cert_name=None):
    target_hostname = override_hostname if override_hostname else hostname
    target_port = override_port if override_port else port
    get_cert_chain(hostname,port,override_cert_name)

# A class for changing the srs portal
class SRSService:
    def __init__(self):
        self.session = requests.Session()
       # self.session.trust_env = True
       # CERT_PATH =  'IntactRootCA.crt'
       # if not os.path.exists(CERT_PATH):
       #     get_root()
        #Root Exists
       # self.session.verify = CERT_PATH
        self.base_url = "https://srssipt.intact.net/crp/"
        self.srs_user =  open('/run/secrets/srs_user', 'r').read().strip()
        self.srs_password = open('/run/secrets/srs_password', 'r').read().strip()

    def login(self):
        # Perform login and store cookies in the session
        login_url = self.base_url + "login"
        payload = {
            'username': self.srs_user,
            'password': self.srs_password
        }
        response = self.session.post(login_url, data=payload)
        response.raise_for_status()

    def get_plan_details(self):
        # Fetch plan details
        plans_url = self.base_url + "plan"
        response = self.session.get(plans_url,params={"planType": "2"},headers={"Referer": self.base_url})
        response.raise_for_status()
        #print(response.text) #We assume this has the initial plan and OID info then we do 
        plan_home_soup = soup(response.text, 'html.parser')
        assignment_plans = []
        users_assigned = []
        plans = []
        rows = plan_home_soup.select('table.table-hover tr')
        for row in rows[1:]:
             cells = row.find_all('td',)
             if len(cells) > 1:
                plan_name = cells[0].text.strip()
                user_assigned = cells[1].text.strip()
                assignment_plans.append(plan_name)
                view_link = row.find('a', {'title': 'View plan'})['href']
                oid = view_link.split('oid=')[1].split('&')[0]
                 # Fetch detailed plan information
                detail_url = self.base_url + "oncall/load"
                detail_response = self.session.get(detail_url, params={"oid": oid, "target": "/oncall/view"}, headers={"Referer": plans_url})
                detail_response.raise_for_status()
                detail_soup = soup(detail_response.text, 'html.parser')

                table_data = []
                detail_rows = detail_soup.select('tr')
                for detail_row in detail_rows:
                    detail_cells = detail_row.find_all('td', {'class': 'desc'})
                    row_data = [cell.text.strip() for cell in detail_cells]
                    if row_data:
                        table_data.append(row_data[-1])

                plans.append({
                    "name": plan_name,
                    "active_user": user_assigned,
                    "available_users": table_data,
                    "oid": oid
                })

        return {"plans": plans}



    def assign_user_to_plan(self, plan_details, assignment, plan):
            # Assign user to plan
            for plan_detail in plan_details['plans']:
                if plan.lower() in plan_detail['name'].lower():
                    available_users = plan_detail['available_users']
                    active_user = plan_detail['active_user']
                    if assignment.lower() in active_user.lower():
                        print(f"{assignment} is already assigned to the plan {plan}", flush=True)
                        return
                    if any(assignment.lower() in user.lower() for user in available_users):
                        print(f"{assignment} is valid", flush=True)
                        oid = plan_detail['oid']
                        user_index = next((i for i, user in enumerate(available_users) if assignment.lower() in user.lower()), None)
                        if user_index is not None:
                            new_redirect_selection = user_index + 1
                            self.session.headers.update({
                                "Origin": f"{self.base_url.split('/crp/')[0] + '/'}",
                                "Referer": f"{self.base_url}plan/phone-redirect",
                            })
                            # First GET request to load the plan
                            response = self.session.get(
                                f"{self.base_url}plan/load",
                                params={"oid": oid, "target": "/plan/phone-redirect"},
                                headers={"Referer": f"{self.base_url}plan?planType=2"}
                            )
                            response.raise_for_status()
                            # First POST request to set the new redirect selection
                            response = self.session.post(
                                f"{self.base_url}plan/phone-redirect",
                                data={"newRedirectSelection": new_redirect_selection, "confirmCallRedirect": ""},
                            )
                            response.raise_for_status()
                            # Second POST request to confirm the redirect change
                            response = self.session.post(
                                f"{self.base_url}plan/phone-redirect",
                                data={"confirmRedirectChange": ""},
                            )
                            response.raise_for_status()
                            return
            print("Name Not In Table", flush=True)

 


def get_srs():
    srs_service = SRSService()
    srs_service.login()
    plan_details = srs_service.get_plan_details()
    return plan_details


def change_srs(user, plan):
    srs_service = SRSService()
    srs_service.login()
    plan_details = srs_service.get_plan_details()
    srs_service.assign_user_to_plan(plan_details, user, plan)
    plan_details = srs_service.get_plan_details()
    return plan_details


#Function to log into the main page of the call system 



if __name__ == '__main__':
    output = change_srs("Orion", "Contact")
    print(output, flush=True)
