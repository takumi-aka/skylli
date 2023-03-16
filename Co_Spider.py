from bs4 import BeautifulSoup
import urllib.request
from urllib.parse import urlparse
from urllib.parse import urljoin
from os import makedirs
import os.path, time, re , csv , shutil , copy
import selenium
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.by import By
from selenium import webdriver 
from webdriver_manager.chrome import ChromeDriverManager

from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed
import random

from threading import Lock

from Arthropod_Base import Arthropod


import multiprocessing 
multiprocessing.set_start_method('spawn', True)

from logging import getLogger, StreamHandler, DEBUG 
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class CoSpider_result():
   
   def __init__(self):
      self.__result_l = []
      return

   def add_r(self, param_r_l = list() , title_r_s = "" , domain_r_s = "" , location_r_s = "") : 
      #
      #if 3 == len(param_r_l) :
      #   return True

      if (title_r_s) and (domain_r_s) and (location_r_s) :
         self.__result_l.append([title_r_s , domain_r_s , location_r_s])
         return True

      return False

   def get_r_list_table(self) :
      return copy.deepcopy(self.__result_l)

   #CoSpider_result end   
   

class CoSpider(Arthropod):
   #needless = "(twitter|instagram|facebook|youtube)"
   power_word = ["問い合" , "お問合"]
   positive_words = ["お名前","メールアドレス","フォーム","コンタクト","送信","問い合","件名" ,"お問合"
                     , "確認" , "進む" , "必須" , "タイトル" , "題名" , "本文" , "連絡先" , "フリガナ" , "内容"] 
   negative_words = ["レンタル","アカウント"] 

   contact_texts = ['お問い合わせ' , '問い合わせ','お問合せ','お問合わせ','御問合せ','御問い合わせ','御問合わせ','お問い合せフォームはこちら','お問い合せ','おといあわせ','ご質問 お問い合わせ', 'ご注文・お問い合わせ','お問い合わせ先','CONTACT','contact','Contact','contact us']
   contact_href_into_words = ['contact','toiawase','otoiawase','faq','inquiry']

   ext = ".csv"
   accepted_urls = {} # {[url] : bool}
   detected_host = {} # {'title : str , 'savepath' : str}
   detected = False

   enc = "UTF-8"
   init_error = False
   
   __hw = False
   url = ""

   def __init__(self , save_file_name="" , url = "",  breath = None , hedden_window = False) :# sname : 結果を保存するFILENAMEを指定している
      super().__init__(save_file_name=save_file_name ,  breath = breath , hedden_window = hedden_window)
      #インストール自体は先に済ませておくべき。
      #ここでは既に行われたアップデートのインストール先のパスが帰ってきている。
      self.__hw = hedden_window
      if not url :
         logger.debug("__init__ failure", url)
      self.url = url
      return None


   def enum_links(self , html, base):# HTMLファイル内にあるlink 、a href　を拾い集める。result = list 
      soup = BeautifulSoup(html, "html.parser")
      links = soup.select("link[rel='stylesheet']")
      links += soup.select("a[href]")
      result = []

      for a in links:
         href = a.attrs['href']
         url = urljoin(base, href) 
         result.append(url)
      return result



   def target_form_detector(self,html):#コンタクトフォームであるか調べる  result {"t" : int "p" : int , "n" : int}
      #<form タグの位置から走査をスタートさせ /form>かデータ末尾に内にある各文字列を評価させる。
      #<title> タグから power_word を探す <title>タグは複数存在する場合がある
      result = {"t" : 0 , "p" : 0 , "n" : 0}
      t_len = len(html) # 末尾
      if 0 == t_len :
         return result      
      low_html = html.lower()   
      t_cnt = 0 ; p_cnt = 0 ; n_cnt = 0 

      def scan(b_tag , e_tag , words):
         nonlocal low_html , t_len

         result = 0 
         t_f_b_idx = low_html.find(b_tag) # 最初の位置
         t_f_e_idx = low_html.find(e_tag) 

         while -1 != t_f_b_idx :
            t_f_b_idx = low_html.find(b_tag , t_f_b_idx ) 
            if -1 != t_f_b_idx :
               t_f_e_idx = low_html.find(e_tag , t_f_b_idx ) 
               if -1 ==  t_f_e_idx :
                  t_f_e_idx = t_len
               #繰り返される別の処理
               for target_str in  words:
                  if -1 != t_f_b_idx :
                     t_pos = html.find(target_str , t_f_b_idx , t_f_e_idx)
                     if -1 != t_pos :
                        result += 1
                         
               t_f_b_idx = t_f_e_idx
         return result

      t_cnt = scan("<title","/title>",self.power_word ) 
      t_cnt += scan("<form","/form>",self.power_word ) 
      p_cnt = scan("<form","/form>",self.positive_words )
      n_cnt = scan("<form","/form>",self.negative_words )

      result = {"t" : t_cnt , "p" : p_cnt , "n" : n_cnt}
      return result



   def search_contactform_url():  # result None / urls(list()) 
      pass


   def first_contact(self) -> str :# コンタクトフォームと思しきurlを返す list()

      def _element_img(_elements , _driver):
         t_element = None
         time.sleep(1+random.uniform(1, 2)) 
         elements_i_a = _driver.find_elements(By.TAG_NAME,'img')    
         for element in elements_i_a:
            a_str = element.get_attribute('alt')
            if a_str == None :
               continue
            for c_str in self.contact_texts :
               if re.search(c_str, a_str):
                  t_element = element.find_element(By.XPATH , './..')
                  if t_element :
                     _elements.append(t_element)
                     break
            if t_element :
               break

         return 

      result = list()

      next_driver = None
      scan_driver = None

      logger.debug("first_contact : " + self.url)

      if not self.breather("life")['life'] :
         self.terminate_flag = True 
         return result


      if re.search(self.needless , self.url):
         return result

      self.driver.get(self.url)  #直後のデータとURLが有効 first first   GET
      
      #GETのあとスリープを入れてselenumの処理結果を安定させる。
      time.sleep(4) 


      if "title" not in self.detected_host.keys(): 
         self.detected_host = {"title" : self.driver.title} 

      elements_l_t = []  

      for c_str in self.contact_texts :
         elements_l_t += self.driver.find_elements(By.PARTIAL_LINK_TEXT,c_str)

      if not elements_l_t : # お問い合わせが img である場合を見て走査
         _element_img(elements_l_t , self.driver)


      if not self.breather("life")['life'] :
         self.terminate_flag = True 
         return result


      if elements_l_t :  
         next_driver =  Arthropod(save_file_name="" , breath = None , hedden_window = self.__hw)           
         for element in elements_l_t :    
            try :
               href_srt = element.get_attribute('href')
               if href_srt == None :
                  continue

               if href_srt in self.accepted_urls:
                  continue

               else :
                  self.accepted_urls[href_srt] = True

               if not self.breather("life")['life'] :
                  self.terminate_flag = True 
                  return result

               logger.debug("first_contact : " + href_srt)

               #二つ目のブラウザ
               if not re.search('@' , href_srt):
                  next_driver.driver.get(href_srt)#直後のデータとURLが有効 

                  time.sleep(4)         
                  html = next_driver.driver.page_source

                  t_f_d = self.target_form_detector(html)
                  if (2 <= t_f_d["p"])and(1 <= t_f_d["t"]) :# 
                     result += [href_srt]
                     break # 301 for element in elements_l_t :   

                  else: # 

                     elements_l_t_end  = [] # 三つ目のブラウザで走査するURL
                     #scan_driver =  webdriver.Chrome(ChromeDriverManager().install(), options=self.options) 
                     scan_driver =  Arthropod(save_file_name="" , breath = None , hedden_window = self.__hw)   
                     # PARTIAL_LINK_TEXT　以外にも有ってもよいか

                     for c_str in self.contact_texts :
                        elements_l_t_end += next_driver.driver.find_elements(By.PARTIAL_LINK_TEXT,c_str)   
         
                     if not elements_l_t_end :
                        _element_img(elements_l_t_end , next_driver.driver)
      
                     href_srt = ""
                     for element_end in elements_l_t_end :    
                        try :
                           
                           href_srt = element_end.get_attribute('href')
                           if (href_srt == None) or (href_srt == '') :
                              continue

                           if href_srt in self.accepted_urls:
                              continue
                           else :
                              self.accepted_urls[href_srt] = True

                           if not self.breather("life")['life'] :
                              self.terminate_flag = True 
                              return result

                           logger.debug("first_contact : " + href_srt)
                           if not re.search('@' , href_srt):
                              scan_driver.driver.get(href_srt) #直後のデータとURLが有効
                              time.sleep(4) 
                              html = scan_driver.driver.page_source
                              t_f_d = self.target_form_detector(html)
                              if (2 <= t_f_d["p"])and(1 <= t_f_d["t"]) :
                                 result += [href_srt]
                                 continue # 320 for element_end in elements_l_t_end :      複数あることを這い処すべき　
                        #except selenium.common.exceptions.StaleElementReferenceException : # 細かくやっていく場合
                        except Exception :
                           break # 320  for element_end in elements_l_t_end :    

                  if scan_driver :
                     scan_driver.browser_close   
                     scan_driver = None
                  if result :
                     break

            #except selenium.common.exceptions.StaleElementReferenceException : # 細かくやっていく場合
            except Exception :
               if scan_driver :
                  scan_driver.browser_close   
                  scan_driver = None
               break  # 301 for element in elements_l_t :   

         if scan_driver :
            scan_driver.browser_close   

         next_driver.browser_close         
     
      return result


   def finish_it(self) -> bool :
      result = False
      r_result = False
      if not self.url :
         return result
      
      if not self.breather("life")['life'] :
         self.terminate_flag = True # ?
         return result


      o = urlparse(self.url)
      hostname = o.hostname

      #全体走査の前にTOPページにあるURLに関連付けられたワードなどから、お問い合わせフォームであるかをチェックする。（時間を端折るため
      self.detected_urls = self.first_contact() #list()が帰ってきている
      if  0 < len(self.detected_urls) :
         #self.detected_host |= {"url" : url} 
         r_result = True
      #else: # 廃止予定
         #r_result = self.recursive_async(self.url , self.url) # 結果が何であれ記録が必要
         # 新たにフラット検索を導入。。。
         # 再帰的検索などの跡地
         #r_result = self.flat_search(self.url , self.url)

      if r_result : # 結果の保存はここで
         self.detected_host |= {"hostname" : hostname}
         result = True 
         self.detected = True
         self.save_to_csv_a()  
      self.browser_close()
         
      return result


   def flat_search(self , url , root_url):

      result = ""
      html = self.driver.page_source
      soup = BeautifulSoup(html, 'html.parser')
      links = [url.get('href') for url in soup.find_all('a')]

      return result


   def get_result_list(self) -> list:
      result = list()
      if not self.detected :
         return result
      
      for a_url in self.detected_urls : # 
         result += [[self.detected_host["title"] , self.detected_host["hostname"] , a_url ]]
      
      return result


#CoSpider end


#開発用

__lock = Lock()
go_on = True
def initializer(string):
   print(f'{string} init thread!')


def worker(url): 
    cs = CoSpider("CoSpiderResult" , url=url , breath=breather ) 
    cs.finish_it()

    return cs.get_result_list()


def breather(switch , save_file_name="" , param_list=list()) : # 戻り値 {}   デバッグ用、オリジナルはskyllaに
    result = {}
    with __lock:    
        match switch:
            case "breath" :
                result = {}

            case "life" :
                result = {"life" : go_on}   

            case "clean_up" :
                try:       
                    f_name = save_file_name
                    if not f_name :  
                        f_name = "eldenring"
                    f = open(f_name + ".csv" , mode="a" , newline="", encoding="UTF-8")                       
                    if param_list :    
                        writer = csv.writer(f)                
                        writer.writerow(param_list)

                finally:
                    f.close()

                result = {}

    return result



if __name__ == "__main__": #開発用
   import multiprocessing 
   multiprocessing.set_start_method('spawn', True)
     
   

   u0 = 'https://www.pref.hokkaido.lg.jp' #謎のエラー

   u1 = "https://wx10.wadax.ne.jp/~yoshidakaya-co-jp/"
   u2 = "https://oec-evaluation.uh-oh.jp/"
   u3 = "https://akubi-office.com/"
   u4 = 'https://kokusai-bs.jp/' 
   u5 = "https://agripick.com/"
   u6 = "https://www.ogb.go.jp/"
   u7 = "https://ecologia.100nen-kankyo.jp/" 
   u8 = "https://www.vill.yomitan.okinawa.jp/"

   target_list = [u8 , u7 , u6 , u5 , u1, u2, u4 ,u5 , u0]

   c0 = "https://www.takunansteel.co.jp/contact/"
   c1 = "http://yanadori.co.jp/contact.html"
   c2 = "http://niigata-tekkotsu.com/contact.html"
   c3 = "https://www.ohtsuka-steel.co.jp/contact/"
   f_c_list = [c0,c1,c2,c3]


   with ProcessPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor:
      futures = []
            #for filename in filenames.keys():
            #    futures.append(executor.submit(worker, filename))
      for url in target_list:
         futures.append(executor.submit(worker, url))

  

   #for url in target_list :
   #   cs = CoSpider("nioh" , url) 
   #   cs.finish_it()


   
