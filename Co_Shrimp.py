

from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.by import By

from urllib.parse import urlparse

import csv ,random , re , time

from threading import Lock
from Arthropod_Base import Arthropod

# 各検索エンジン用の処理無いしクラスを置く
# 入力　検索ワード
# 出力  URLのリスト->CSVとインスタンス両方




class GoogleShrimp(Arthropod) :
  
    search_word = ""
    def __init__(self , search_word = "" , save_file_name="",  breath = None , hedden_window = False) :

        super().__init__(save_file_name=save_file_name ,  breath = breath , hedden_window = hedden_window)
        self.search_word = search_word

        return 


    def boil(self) :
        self.driver.get('https://google.com/search?q=' + self.search_word  + '&filter=0')

        time.sleep(1+random.uniform(1, 3.7)) 
        elem = self.driver.find_element(By.NAME,'q')
        #elem.send_keys(self.search_word)
        time.sleep(2+random.uniform(1, 3.7)) 
        elem.send_keys(Keys.ENTER) 
        time.sleep(3+random.uniform(1, 3.7)) 

        elem = self.driver.find_elements(By.TAG_NAME,'A')
        r_list = []

        while True :

            for elem_h3 in self.driver.find_elements(By.XPATH, '//a/h3'):
                elem_a = elem_h3.find_element(By.XPATH , '..')  
                o = urlparse(elem_a.get_attribute('href'))
                host_url = o.scheme + "://" + o.hostname
                if not re.search(self.needless , host_url):
                    r_list += [[elem_h3.text , host_url]]
                print(elem_h3.text)
                print(elem_a.get_attribute('href'))
            
            try:
                next_page = self.driver.find_element(By.ID , "pnnext").get_attribute("href")
                #if next_page == [] :
            except:
                break

            if not self.breather("life") :
                break
            
            self.driver.get(next_page)      
            time.sleep(2.5+random.uniform(1, 3.7))  
            
        self.breather("breath" , param_list=r_list)
        self.breather("save" , save_file_name=self.save_file_name , param_list=r_list)

        return
# GoogleShrimp class end


class BillShrimp(Arthropod) :
    search_word = ""
    def __init__(self , search_word = "" , save_file_name="",  breath = None , hedden_window = False) :

        super().__init__(save_file_name=save_file_name ,  breath = breath , hedden_window = hedden_window)
        self.search_word = search_word

        return 

    def boil(self) :
        self.driver.get('https://www.bing.com/search?q=' + self.search_word  + '&filter=0')
        time.sleep(1+random.uniform(1, 3.7)) 
        elem = self.driver.find_element(By.NAME,'q')
        #elem.send_keys(self.search_word)
        time.sleep(2+random.uniform(1, 3.7)) 
        elem.send_keys(Keys.ENTER) 
        time.sleep(3+random.uniform(1, 3.7)) 

        elem = self.driver.find_elements(By.TAG_NAME,'A')
        r_list = []
        while True :
            #//body/div/main/ol/li/ul/li/div/h2/a
            elements = self.driver.find_elements(By.CLASS_NAME, 'b_algo')
            for elem_h3 in elements:
                elem_a = elem_h3.find_element(By.XPATH , '//h2/a')  
                o = urlparse(elem_a.get_attribute('href'))
                host_url = o.scheme + "://" + o.hostname
                if not re.search(self.needless , host_url):
                    r_list += [[elem_h3.text , host_url]]
                print(elem_h3.text)
                print(elem_a.get_attribute('href'))
            
            try:
                next_page = self.driver.find_element(By.CLASS_NAME , "sb_pagN").get_attribute("href")
                if next_page == [] :
                    break
            except:
                break

            self.driver.get(next_page)      
            time.sleep(2.5+random.uniform(1, 3.7))  

        return



__lock = Lock()
go_on = True

def breather(switch , save_file_name="" , param_list=list()) : # 戻り値 {}   デバッグ用、オリジナルはskyllaに
    result = {}
    with __lock:    
        match switch:
            case "breath" :
                result = {}

            case "life" :
                result = {"life" : go_on}   

            case "save" :
                try:       
                    f_name = save_file_name
                    if not f_name :  
                        f_name = "eldenring.csv"
                    f = open(f_name , mode="a" , newline="", encoding="UTF-8")       
                    for a_list in param_list :
                        writer = csv.writer(f)
                        writer.writerow(a_list)
                finally:
                    f.close()

                result = {}

    return result


if __name__ == '__main__':
    import multiprocessing 

    multiprocessing.set_start_method('spawn', True)

    gs = GoogleShrimp(search_word="食品加工 静岡" , save_file_name="検索結果.csv" , breath = breather)
    gs.boil() 


