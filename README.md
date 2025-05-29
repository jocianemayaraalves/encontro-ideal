# Encontro Ideal - Agenda para famílias

Este projeto é um app feito com Streamlit que permite que membros de uma família marquem seus horários disponíveis para encontros. Os dados são armazenados no Firebase Firestore, garantindo que várias pessoas em dispositivos diferentes possam participar usando um código único da família.

## Funcionalidades

- Entrada de código da família para carregar dados privados  
- Seleção de datas no mês atual e próximo mês  
- Marcação de horários disponíveis por usuário  
- Armazenamento em banco Firestore  
- Cálculo automático dos horários em comum para a família

## Como usar

### Pré-requisitos

- Conta Google para criar projeto Firebase e banco Firestore  
- Configurar as credenciais Firebase conforme descrito abaixo  
- Ter Python 3.7+ instalado

### Instalação

1. Clone este repositório  
2. Crie e ative um ambiente virtual (recomendado)  
3. Instale as dependências:

```bash
pip install -r requirements.txt
