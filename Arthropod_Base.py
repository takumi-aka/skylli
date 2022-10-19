from selenium import webdriver 
from webdriver_manager.chrome import ChromeDriverManager

from logging import getLogger, StreamHandler, DEBUG 
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class Arthropod :
    lucky_urls = ("https://docs.google.com/forms","https://forms.gle")
    needless = "(twitter|instagram|facebook|youtube|indeed|baseconnect|yahoo|townpage|domonet|news|docomo|amazom|kakaku|oricon|wikipedia|tiktok)"
    negative_multibyte_words = ["派遣","求人","地図","アルバイト","ハローワーク","マピオン","goo地図"] 
    options = None
    driver = None
    save_directory = "./result_URLs"
    save_file_name = ""
    breather = None
    terminate_flag = False
    detected_url = {} # {'title : str , ''url' : str , 'savepath' : str}

    def __init__(self , save_file_name="" , breath = None , hedden_window = False) :
        try:
            self.options = webdriver.ChromeOptions()
            self.options.add_argument("--window-size=1920,1080")
            if hedden_window :
                self.options.add_argument('--headless')
            self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=self.options) 

            self.save_file_name = save_file_name 
            if breath is not None : 
                if callable(breath):
                    self.breather = breath
        except:
            logger.debug("__init__ failure")
            return None


    def save_to_csv_a(self) :
        if self.detected_url :
            data_list = [self.detected_url["title"] , self.detected_url["hostname"] , self.detected_url["url"] , str(id(self)) , str(id(self.driver))]        
        result = self.breath("save" , save_file_name=self.save_file_name  , param_list=data_list) 
        return result


    def browser_close(self) :
        if self.driver :
            self.driver.close() 
