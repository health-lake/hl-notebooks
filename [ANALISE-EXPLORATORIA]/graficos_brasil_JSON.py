#############################################################
# VER FINAL DO CÓDIGO PARA DESCRIÇÃO DE COMO USAR O PROGRMA #
#############################################################

import requests
import json
import matplotlib.pyplot as plt
import xlrd, datetime
import numpy as np
from scipy.stats import norm, hypsecant
from scipy import optimize
#import scipy.integrate as integrate
from datetime import date, timedelta

class Dados:
     def __init__(self, nome, dia, confirmed, confirmed_in_date, deaths, deaths_in_date):
        self.nome = nome
        self.dia = dia
        self.confirmed = confirmed
        self.confirmed_in_date = confirmed_in_date
        self.deaths = deaths
        self.deaths_in_date = deaths_in_date
       
# início funções    
def modelo (x,a,b,c,d): #modelo dados acumualdos
    return a*np.tanh(b*x + c) + d

def derivada (x,a,b,c,d): #modelo dados por dia = derivada modelo dados acumulados
    return a*b*(np.cosh(c + b*x))**(-2)

def gerarJSON(cidade):
    xdados = np.arange(1, len(cidade.dia)+1) #array para o eixo x dos dados
    diamax =  len(cidade.dia)+100
    xmodelo = np.arange(1,diamax) #array para o eixo x do fit do modelo
    x = [date.fromisoformat(cidade.dia[0])] #array para os labels dos ticks do eixo x
    for i in range(1, diamax):
        x.append(x[0]+timedelta(days=i))

    # CASOS CONFIRMADOS
    dadosConfirmed = cidade.confirmed #dados para o acumulado
    poptConfirmed, _ = optimize.curve_fit(modelo, xdados, dadosConfirmed, maxfev=150000) #fit do modelo
    yConfirmed = modelo(xmodelo, *poptConfirmed) #dados do fit
    sigmaConfirmed = (np.mean((dadosConfirmed-modelo(xdados, *poptConfirmed))**2))**0.5 #desvio padrão dos dados
    # CASOS POR DIA
    dadosConfirmedInDate = cidade.confirmed_in_date #dados por dia
    yConfirmedInDate = derivada(xmodelo, *poptConfirmed) #dados do modelo por dia
    sigmaConfirmedInDate = (np.mean((dadosConfirmedInDate-derivada(xdados, *poptConfirmed))**2))**0.5 #desvio padrão dos dados
    
    
    # MORTES CONFIRMADAS
    dadosDeaths = cidade.deaths #dados para o acumulado
    poptDeaths, _ = optimize.curve_fit(modelo, xdados, dadosDeaths, maxfev=150000) #fit do modelo
    yDeaths = modelo(xmodelo, *poptDeaths) #dados do fit
    sigmaDeaths = (np.mean((dadosDeaths-modelo(xdados, *poptDeaths))**2))**0.5 #desvio padrão dos dados
    # MORTES POR DIA
    dadosDeathsInDate = cidade.deaths_in_date #dados por dia
    yDeathsInDate = derivada(xmodelo, *poptDeaths) #dados do modelo por dia
    sigmaDeathsInDate = (np.mean((dadosDeathsInDate-derivada(xdados, *poptDeaths))**2))**0.5 #desvio padrão dos dados
    
  
    output = ['"fit":{"cases":{"a":' + str(poptConfirmed[0]) + ', "b":' + str(poptConfirmed[1]) + ', "c": ' + str(poptConfirmed[2]) + ', "d":' + str(poptConfirmed[3]) + '}, "deaths":{{"a":' + str(poptDeaths[0]) + ', "b":' + str(poptDeaths[1]) + ', "c": ' + str(poptDeaths[2]) + ', "d":' + str(poptDeaths[3]) + '}, "dados":']
    for dia in range(len(x)-1):
        output.append('{"date": ' + date.isoformat(x[dia]) + ':{"confirmed": ' + str(yConfirmed[dia]) + ', "confirmed_in_date": ' + str(yConfirmedInDate[dia]) + ', "deaths: ' + str(yDeaths[dia]) + ', "deaths_in_date": ' + str(yDeathsInDate[dia]) + '}')
    output.append('}')
    return output
  

#fim funções


##################
### COMO USAR ####
##################

'''
Definir um objeto na forma: cidade = Dados(nome, dia, confirmed, confirmed_in_date, deaths, deaths_in_date)
Para gerar os gráficos usar a função plotarGraficos na forma: plotarGraficos(cidade)
'''


# inicio formatacao dos dados
api_url = 'https://brasil.io/api/dataset/covid19/caso_full/data?place_type=state&page_size=10000' # API COVID-19 Brasil.io
api = requests.get(api_url).json()['results']
Brasil = Dados("Brasil", [], [], [], [], [])


for item in api:
    dia = item['last_available_date']
    Brasil.dia.append(dia)
Brasil.dia = list(dict.fromkeys(Brasil.dia))[::-1]

Brasil.deaths = [0]*len(Brasil.dia)
Brasil.confirmed = [0]*len(Brasil.dia)
Brasil.confirmed_in_date = [0]*len(Brasil.dia)
Brasil.deaths_in_date = [0]*len(Brasil.dia)


for i in range(len(Brasil.dia)):
    for j in range(len(api)):
        if Brasil.dia[i] == api[j]['last_available_date']:
            Brasil.deaths[i] += api[j]['last_available_deaths']
            Brasil.deaths_in_date[i] += api[j]['new_deaths']
            Brasil.confirmed[i] += api[j]['last_available_confirmed']
            Brasil.confirmed_in_date[i] += api[j]['new_confirmed']


outputFitJSON = gerarJSON(Brasil)

#print(outputFitJSON)

#print("fim do programa")