# Unica Student Personal Page Scraper

import requests
import jsonpickle
import json
from bs4 import BeautifulSoup

INTERFACE_VERSION = "1.0 Beta"
BASE_URL_HOME = "https://unica.esse3.cineca.it/auth/studente/HomePageStudente.do"
BASE_URL = "https://unica.esse3.cineca.it/"
PAYMENT_RECAP_URL = "https://unica.esse3.cineca.it/auth/studente/Tasse/ListaFatture.do"

MATRICOLA_LENGHT = 11

LOGIN_OK, LOGIN_ERR, LOGIN_UNKNOWN, LOGIN_NO_CREDENTIAL, LOGIN_PENDING, LOGIN_OK_MULTIPLE_CAREER = range(6)


class UnicaInterface():  
    
    def __init__(self):
        self.logged = LOGIN_PENDING
        self.session = requests.Session()


    def __auth(self, username, password):
        session = self.session
        session.auth = (username, password)        
        self.auth = session.post(BASE_URL_HOME)
       

    def isLogged(self):      
        return self.logged == LOGIN_OK


    def login(self, username = '', password = ''):
        if username == '' or password == '':
            if not hasattr(self, 'username') or not hasattr(self, 'password'):
                return LOGIN_NO_CREDENTIAL
            else:
                self.__auth(self.username, self.password)       
               
        else:
            self.__auth(username, password)

        response = self.session.get(BASE_URL_HOME)
        self.response = response
        internalSoup = BeautifulSoup(response.text, 'html.parser')
        title = str(internalSoup.title.string)
        #print(title)
        if title.find("Esse3 - Messaggio") > -1:
            self.logged = LOGIN_ERR
            return LOGIN_ERR
        elif title.find("Home Studente") > -1 or title.find("Scelta carriera") > -1:
            if username != '' or password != '':
                self.username = username
                self.password = password

            self.raw_page = response.text
            self.logged = LOGIN_OK
            if title.find("Scelta carriera") > -1:
                if hasattr(self, 'choosen_career'):
                    if self.choosen_career != -1:
                        return self.selectCareer(self.choosen_career)
                return LOGIN_OK_MULTIPLE_CAREER
            else:
                self.matricola = self.getMatricola()
                #print(self.matricola)
                return LOGIN_OK
        else:
            self.logged = LOGIN_UNKNOWN
            return LOGIN_UNKNOWN
        
    def getCareers(self):
        page = self.response.text
        internalSoup = BeautifulSoup(page, 'html.parser')

        careers = "["
        rows = internalSoup.find("tbody").find_all("tr")

        for row in rows:
            cells = row.find_all("td")

            matricola = cells[0].string
            corso_studio = cells[2].string
            tipo_corso = cells[1].string
            stato_corso = cells[3].string
            link = cells[4].find("a", href=True).get("href")
                    
            json = '{'
            json = json + '"matricola" : "'+ matricola + '",'
            json = json + '"corso_studio" : "' + corso_studio + '",'
            json = json + '"tipo_corso" : "'+ tipo_corso + '",'
            json = json + '"stato_corso" : "'+ stato_corso + '",'
            json = json + '"link" : "'+ link + '"},'

            careers = careers + json 

        careers = careers[:-1] + "]"
        self.careers = careers
        return careers

    def selectCareer(self, careerNumber):
       
        careers = json.loads(self.getCareers())

        choosen_career = careers[int(careerNumber)]
        link = choosen_career['link']
        full_link = BASE_URL + "/" + link
      
        response = self.session.get(full_link)

        internalSoup = BeautifulSoup(response.text, 'html.parser')
       
        title = str(internalSoup.title.string)

        if title.find("Esse3 - Messaggio") > -1:
            self.logged = LOGIN_ERR
            return LOGIN_ERR
        elif title.find("Home Studente") > -1 or title.find("Scelta carriera") > -1:
           
            self.raw_page = response.text
            self.logged = LOGIN_OK
            if title.find("Scelta carriera") > -1:
                self.choosen_career = -1
                return LOGIN_ERR
            else:
                self.choosen_career = careerNumber
                self.matricola = self.getMatricola()
                #print(self.matricola)
                return LOGIN_OK
        else:
            self.logged = LOGIN_UNKNOWN
            return LOGIN_UNKNOWN

    def setCredentials(self, username, password):
        self.username = username
        self.password = password


    def setUsername(self, username):
        self.username = username


    def setPassword(self, password):
        self.password = password


    def getPaymentPage(self):
        if self.isLogged():
            response = self.session.get(PAYMENT_RECAP_URL)
            return response.text

        return "Please login first"


    def getPayments(self):
        taxes = []
        page = self.getPaymentPage()
        if page == "Please login first":
            if self.isLogged:
                self.login()
            else:
                return taxes
        
        internalSoup = BeautifulSoup(page, 'html.parser')
        rows = internalSoup.find("tbody").find_all("tr")
        for row in rows:
            cells = row.find_all("td")

            id_fattura = cells[0].string
            iuv = cells[1].string
            codice_fattura = cells[2].string         
            
            desc = cells[3].text
            desc = desc.replace("\n", "")
            desc = desc.replace("\t", "")
            desc = desc.replace("                                             ", "")
            desc = desc.replace("\\u200b", "")
            desc = desc[1:]

            scadenza = cells[4].text
            importo = cells[5].text

            if 'confermato' in cells[6].text:
                status = "Pagato"
            else:
                status = "Da pagare"
    
            tax = UnicaTax( 
                            id_fattura = id_fattura,
                            iuv=iuv, 
                            fattura=codice_fattura,
                            descrizione=desc,
                            scadenza=scadenza,
                            stato=status,
                            importo=importo
                            )
            if self.matricola in tax.descrizione:
                taxes.append(tax)
               
        return taxes


    def getPaymentsJSON(self):
        taxes = self.getPayments()
       
        if taxes == []:
            return "{}"
            
        taxes_json = "["
        for tax in taxes:
            taxes_json = taxes_json + tax.getJSON() + ","
        taxes_json = taxes_json[:-1] + "]"
        return taxes_json #jsonpickle.encode(taxes)


    def getNewTax(self):
        if hasattr(self, 'last_taxes'):
            last_taxes = self.last_taxes
            current = self.getPaymentsJSON()
            if last_taxes == current:
                return "{}"
            else:
                self.last_taxes = current
                #dobbiamo vedere quali sono le nuove tasse
                return current.replace(last_taxes, "")                
        else:
            self.last_taxes = self.getPaymentsJSON()
            return "{}"


    def __initAnalyzer(self):
        if not hasattr(self, 'soup'):
            self.soup = BeautifulSoup(self.raw_page, 'html.parser')


    def getPage(self):
        if self.logged != LOGIN_OK:
            return "You must login first"
        else:
            response = self.response            
            return response.text
   

    def getUserName(self):
        full_name = ""
        if self.isLogged:
            self.__initAnalyzer()
            name_raw = self.soup.find_all(class_="masthead_usermenu_user_name")[0].string
            names = name_raw.split()
            for name in names: 
                name = name[0] + name[1:].lower()
                full_name = full_name + " " 

        return full_name


    def getMatricola(self):
        if self.isLogged:
            self.__initAnalyzer()
            #name_raw = self.soup.find_all(class_="masthead_usermenu_user_name")[0].string
            matricola = self.soup.find_all(class_="pagetitle_title")[0].string
            n_pos = int(matricola.find("N. ")) + 3
            last_pos = int(n_pos + MATRICOLA_LENGHT)
            matricola = matricola[n_pos:last_pos]
            #print(matricola)
            return matricola
        return ""
    

    def getTaxesUserReadable(self, taxes_json):
        botResponse = "Riepilogo Tasse\n\n"
        pending = 0
        paid = 0

        taxes = json.loads(taxes_json)

        for tax in taxes:
            if tax['stato'] == 'Pagato':
                paid = paid + 1 
            else:
                pending = pending + 1


        botResponse = botResponse + "Tasse da pagare : " + str(pending)
        botResponse = botResponse + "\nTasse pagate : " + str(paid)
        if pending == 0: 
            botResponse = botResponse + "\n\n\U00002705 Tutte le tasse sono state pagate \U0001F60A"

        botResponse = botResponse + "\n=================================="
        botResponse = botResponse + "\nElenco tasse"
        for tax in taxes:            
            if tax['stato'] == "Pagato":
                stato = "\U00002705"
            else:
                stato = "\U000026A0"
            botResponse = botResponse + "\n\n"
            botResponse = botResponse +  stato + " " + tax["stato"]
            botResponse = botResponse + "\n\U0001F550 Scadenza " + tax["scadenza"] 
            botResponse = botResponse + "\n\U0001F4B8 Totale : " + tax["importo"]
            botResponse = botResponse + "\n\U0001F194 ID Tassa : [" + tax["id_fattura"]
            botResponse = botResponse + "]\n\U0001F4C4 Descrizione : " + tax["descrizione"]
            #botResponse = botResponse + "\n Link : " + tax['link']
            
        return botResponse


class UnicaTax():
    
    def __init__(self, id_fattura = "", iuv = "", fattura="", stato= "", importo= "", descrizione= "", scadenza="", link=""):
        self.id_fattura = id_fattura
        self.iuv = iuv
        self.fattura = fattura
        self.stato = stato
        self.importo = importo
        self.descrizione = descrizione
        self.scadenza = scadenza
        self.link = link
    
    def __str__(self):
        return "Tassa ["+str(self.id_fattura) + "]:\
                (" + str(self.fattura) + ")\
                IUV : ["+str(self.iuv) + "],\
                Importo : " + str(self.importo) + ", \
                Scadenza : " + str(self.scadenza) + ", \
                Stato pagamento : " + str(self.stato) + ",\
                Descrizione : " + str(self.descrizione)

    def getJSON(self):
        json = '{'
        json = json + '"id_fattura" : "'+str(self.id_fattura)+ '",'
        json = json + '"iuv" : "' +str(self.iuv)+ '",'
        json = json + '"fattura" : "'+str(self.fattura)+ '",'
        json = json + '"stato" : "'+str(self.stato)+ '",'
        json = json + '"importo" : "'+str(self.importo)+ '",'
        json = json + '"descrizione" : "'+str(self.descrizione)+ '",'
        json = json + '"link" : "'+str(self.link)+ '",'
        
        json = json + '"scadenza" : "'+str(self.scadenza)+ '"}'

        return json 
    
    def setId(self, id_fattura):
        self.importo = id_fattura

    def setImporto(self, importo):
        self.importo = importo
    
    def setFattura(self, fattura):
        self.fattura = fattura
    
    def setStato(self, stato):
        self.stato = stato

    def setDescrizione(self, descrizione):
        self.descrizione = descrizione
    
    def setIuv(self, iuv):
        self.iuv = iuv

    def setScadenza(self, scadenza):
        self.scadenza = scadenza

    def setLink(self, link):
        self.link = link

    # getters 
    def getIdFattura(self):
        return self.id_fattura

    def getImporto(self):
        return self.importo
    
    def getFattura(self):
        return self.fattura
    
    def getStato(self):
        return self.stato

    def getDescrizione(self):
        return self.descrizione
    
    def getIuv(self):
        return self.iuv

    def getScadenza(self):
        return self.scadenza

    def getLink(self):
        return self.link