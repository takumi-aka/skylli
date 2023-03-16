







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


   def __download_file_selenium(self , url): # result {'url' : str ,'savepath' : str ,  'isthis' bool}

      try:
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
