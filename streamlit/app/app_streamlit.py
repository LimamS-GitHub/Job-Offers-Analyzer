import asyncio
from datetime import date,timedelta
import os

from time import time
import re
from typing import List, Dict, Tuple, Optional
import time as time_module
import json
import google.generativeai as genai
from dotenv import load_dotenv
import httpx
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode, quote_plus
import pandas as pd
import streamlit as st


if "all_offers" not in st.session_state:
    st.session_state.all_offers = []


pg = st.navigation(["Overview.py", "Job_collection.py", "Analysis.py"])

pg.run()
