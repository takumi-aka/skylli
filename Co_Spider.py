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
      if 3 == len(param_r_l) :
         return True

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

   contact_texts = ['お問い合わせ' , '問い合わせ','お問合せ','お問合わせ','御問合せ','御問い合わせ','御問合わせ','お問い合せフォームはこちら','お問い合せ','おといあわせ','ご質問 お問い合わせ', 'ご注文・お問い合わせ','お問い合わせ先','CONTACT','contact','contact us']
   contact_href_into_words = ['contact','toiawase','otoiawase','faq','inquiry']

   ext = ".csv"
   accepted_urls = {} # {[url] : bool}
   #detected_url = {} # {'title : str , ''url' : str , 'savepath' : str}
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


   def __download_file_selenium(self , url): # result {'url' : str ,'savepath' : str ,  'isthis' bool}

      try:#ここをダウンロードからコンテンツチェックに変える
         result = {"url" : "" , "savepath" : "" ,  "isthis" : False , "needless" : False}
         o = urlparse(url)

         result["url"] = url 
         #savepath 

         savepath = self.save_directory + "/" + o.netloc 
         if o.path : 
            savepath +=  o.path 
            if re.search(r"/$", savepath):
               savepath += o.query
            else : savepath += "/" + o.query   
         else : savepath += "/"
         if re.search(r"/$", savepath):#末尾に / が無いからと言ってディレクトリとは限らない。
            savepath += "res.html"

         result["savepath"] = savepath

         if re.search(self.needless , savepath):
            result["needless"] = True
            return result #savepath

         savedir = os.path.dirname(savepath)

         if os.path.exists(savepath): 
            return result

         logger.debug("get=" + url)
         self.driver.get(url)#直後のデータとURLが有効

         #GETのあとスリープを入れてselenumの処理結果を安定させる。
         time.sleep(5) 

         time.sleep(1+random.uniform(2, 2))
         t_len = len(self.driver.page_source)
         t_url = self.driver.current_url

         if "title" not in self.detected_url.keys(): #最初のページのタイトルだけを得る
            self.detected_url = {"title" : self.driver.title} 
         #問い合わせフォームであるかをテストするコードを入れる場所
         res = self.target_form_detector(self.driver.page_source)   # result {"t" : int , "p" : int , "n" : int} / None
         if (2 <= res["p"])and(1 <= res["t"]) :
         #p , t  それぞれの値から評価　フローを変える
         #コンタクトフォームと思しきHTMLは保存しておくべき 解析用サンプル（基本保存するのはこれだけでよい
            result["isthis"] = True
            self.detected = True

            o = urlparse(t_url)

            savepath = self.save_directory + "/" + o.netloc 
            if o.path : 
               savepath +=  o.path 
               if re.search(r"/$", savepath):
                  savepath += o.query
               else : savepath += "/" + o.query   
            else : savepath += "/"
            if re.search(r"/$", savepath):#末尾に / が無いからと言ってディレクトリとは限らない
               if 0 <= t_len :# コンテンツあり。ディレクトリではない。
                  if not re.search(r".(html|htm|cgi)$", savepath):# ここにファイル名が無ければ
                     savepath += "res.html"

            savedir = os.path.dirname(savepath)
            result["savepath"] = savepath

            self.detected_url |= {"url" : url}

            if os.path.exists(savepath): 
               return savepath

         if not os.path.exists(savedir):
            print("mkdir=", savedir)
            os.makedirs(savedir) #日本語でディレクトリ名を作成できない
      
         w_str = self.driver.page_source
         with open(savepath, mode="w", encoding=self.enc) as f: #保存するためにエンコードを先んじて取得しておくべき
            f.write(w_str)
            f.close
           
         time.sleep(1+random.uniform(2, 2))
         return result

      except selenium.common.exceptions.NoSuchWindowException :
         logger.debug("NoSuchWindowException:" + url)
         return None

      except:
         logger.debug("ダウンロード失敗:" + url)
         return None


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
      p_cnt = scan("<form","/form>",self.positive_words )
      n_cnt = scan("<form","/form>",self.negative_words )

      result = {"t" : t_cnt , "p" : p_cnt , "n" : n_cnt}
      return result


   def __download_file(self , url):  #URL次第ではパスが作れずエラーを吐く
   #Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36

      try:#ここをダウンロードからコンテンツチェックに変える
         print("download=", url)
         #urlretrieve(url, savepath)
         user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
         req = urllib.request.Request(url, headers={'User-Agent': user_agent}, method='GET')
         with urllib.request.urlopen(req) as response:
            print(response.getcode())
            print(response.info())
            t_url = response.geturl()
            t_len = response.length
            o = urlparse(t_url)

            savepath = "./" + o.netloc + o.path
            if re.search(r"/$", savepath):#末尾に / が無いからと言ってディレクトリとは限らない。
               savepath += "index.html"
            else:
               if 0 <= t_len :# コンテンツあり。ディレクトリではない。
                  savepath += "/index.html"
            savedir = os.path.dirname(savepath)

            if os.path.exists(savepath): 
               return savepath

            if not os.path.exists(savedir):
               print("mkdir=", savedir)
               os.makedirs(savedir) #日本語でディレクトリ名を作成できない→出来た
            #data = urllib.request.urlopen(url).read()
            with open(savepath, mode="wb") as f:
               f.write(response.read())
            #   print(response.read().decode(), file=save_file)
         time.sleep(1+random.uniform(1, 2))
         return savepath
      except urllib.error.HTTPError as e:
         print(e)
         print(e.code)
         print(e.reason)
      except urllib.error.URLError as e:
         print(e)
         print(e.code)
         print(e.reason)

      except:
         print("ダウンロード失敗:", url)
         return None

   def first_contact(self) -> str :# コンタクトフォームと思しきurlを返す | 見つからなければ　""

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

      result = ""

      next_driver = None
      scan_driver = None

      logger.debug("first_contact : " + self.url)

      if not self.breather("life")['life'] :
         self.terminate_flag = True 
         return result


      self.driver.get(self.url)  #直後のデータとURLが有効 first first   GET
      
      #GETのあとスリープを入れてselenumの処理結果を安定させる。
      time.sleep(4) 


      if "title" not in self.detected_url.keys(): 
         self.detected_url = {"title" : self.driver.title} 

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
               next_driver.driver.get(href_srt)#直後のデータとURLが有効 
               time.sleep(4)         
               html = next_driver.driver.page_source

               t_f_d = self.target_form_detector(html)
               if (2 <= t_f_d["p"])and(1 <= t_f_d["t"]) :# 
                  result = href_srt
                  break # 301 for element in elements_l_t :   

               else: # 

                  elements_l_t_end  = []
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
                        scan_driver.driver.get(href_srt) #直後のデータとURLが有効
                        time.sleep(4) 
                        html = scan_driver.driver.page_source
                        t_f_d = self.target_form_detector(html)
                        if (2 <= t_f_d["p"])and(1 <= t_f_d["t"]) :
                           result = href_srt
                           break # 320 for element_end in elements_l_t_end :     
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
      f_s_r_href = self.first_contact()
      if f_s_r_href :
         #f_s_r_href = o.scheme + '/' + hostname + f_s_r_href
         self.detected_url |= {"url" : f_s_r_href} 
         r_result = True
      #else:
         #r_result = self.recursive_async(self.url , self.url) # 結果が何であれ記録が必要
         # 新たにフラット検索を導入。。。
         # 再帰的検索などの跡地
         #r_result = self.flat_search(self.url , self.url)

      if r_result : # 結果の保存はここで
         self.detected_url |= {"hostname" : hostname}
         result = True 
         self.detected = True
         self.save_to_csv_a()  
      self.browser_close()

      #いずれにしてもここでファイルを削除したい
      rmtd= self.save_directory + '/' + hostname + '/'
      if(os.path.isdir(rmtd) == True):
         try:
            if not os.access(rmtd, os.W_OK):
               os.chmod(rmtd, 755)
            shutil.rmtree(rmtd)
         except:
            pass
         
      return result


   def recursive_async(self , url, root_url):
      
      nest = 0
      result = False

      r_selenium = self.__download_file_selenium(url)  #ドメインであるはずであるため

      if True == r_selenium["needless"] : return result #不要なURLである印がある
      savepath = r_selenium["savepath"] 
      if savepath is None: return result
      if savepath in self.accepted_urls: return result # 既に辞書にあるURLである
      if self.detected : return self.detected 

      self.accepted_urls[savepath] = True
      logger.debug("recursiv_sync=", url)

      #encodingは各サイトで幾つか試す必要があるだろう  
      try :
         html = open(savepath, "r", encoding="UTF-8").read()  #ワードプレスはこれ
         self.enc="UTF-8"   #一切効いてない
      except :
         try :
            html = open(savepath, "r", encoding="CP932").read()  #今のところそれ以外
            self.enc="CP932"
         except :
            try :
               html = open(savepath, "r", encoding="shift_jis").read()  #今のところそれ以外-
               self.enc="shift_jis"
            except :

               return "対策求" # まだ先はあろう

      links = self.enum_links(html, url)
      for link_url in links:   # self.detectedが来るまではURLをひたすら走査しなくなった時点で終わる。この辺に強制終了を置ける。
         if (link_url.find(root_url) != 0) and (not re.search(self.lucky_urls , link_url)) :          
            continue   

         if re.search(r".(css|css2)", link_url): continue
         if re.search(r".(png|wmv|avi|mpeg|mp4|pdf|gif|jpg)$", link_url): continue
         if re.search(r".(html|htm|cgi)$", link_url):
            if self.detected : break  
            ++nest
            if 2 > nest :
               self.recursive_async(link_url, root_url)   # ネストのチェック

            --nest   
            continue

         if not self.breather("life")['life'] :
            self.terminate_flag = True
            break

         if self.detected : break

         self.__download_file_selenium(link_url)
 
      return self.detected


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
      result = [self.detected_url["title"] , self.detected_url["hostname"] , self.detected_url["url"], str(id(self)) , str(id(self.driver))]  
      
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


   
