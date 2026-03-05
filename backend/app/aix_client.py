"""
Initialises the aiXplain SDK client using the v2 pattern:

    from aixplain import Aixplain
    aix = Aixplain(api_key="<AIXPLAIN_API_KEY>")

Import `aix` from this module wherever you need to access the SDK.
config.py is imported first to guarantee load_dotenv() has already run.
"""

from aixplain import Aixplain
from app.config import AIXPLAIN_API_KEY

aix = Aixplain(api_key=AIXPLAIN_API_KEY)
