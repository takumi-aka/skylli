import os
import PySimpleGUI as sg
import csv

#UI 機能統合など
from threading import Lock
import concurrent
from concurrent.futures import ThreadPoolExecutor

import tkinter as tk

import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome import service as fs
from selenium import webdriver 
from Co_Shrimp import GoogleShrimp , GoogleShrimp_result
from Co_Spider import CoSpider , CoSpider_result


worker_thread_with = None
thread_mode = {'noop' : 0 ,'active' : 1 , 'destroy' : 2 } 
shrimp_stat = thread_mode['noop']
spider_stat = thread_mode['noop']

window_keys = ('-g-search-start-' , '-g-search-break-' , '-g-search-words-start-' , '-g-search-words-break-'
             ,'-spider-start-' ,  '-spider-break-' ,'-spin-t-cnt-' , '-spider-cbox-hw-' , '-shrimp-cbox-hw-')
shrimp_btn_enable = (window_keys[0] , window_keys[2] , window_keys[3], window_keys[4] , window_keys[5] , window_keys[6] , window_keys[7] ,window_keys[8])
shrimps_btn_enable = (window_keys[0] , window_keys[1], window_keys[2] , window_keys[4] , window_keys[5] , window_keys[6] , window_keys[7] ,window_keys[8])
spider_btn_enable = (window_keys[0] , window_keys[1],window_keys[2] , window_keys[3],window_keys[4] , window_keys[6],window_keys[7] ,window_keys[8])


#coshrimp  #検索エンジンからデータをあさるクラス
#cospider  #各サイトにコンタクトフォームが存在するか走査するクラス

shrimp_executor = None #coshrimp実行の為のサブスレッド

__lock = Lock() #クリティカルセクション
go_on = True
search_result_all = {}
last_result_object = None

def initializer(string):
    print(f'{string} init thread!')


def update_chrome_install() :
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')

    path = ChromeDriverManager().install() 
    print(f'{path} init thread!')
    chrome_service = fs.Service(executable_path=path) 
    webdriver.Chrome(service=chrome_service, options=options)
    webdriver.Chrome.close

    #webdriver.Chrome(ChromeDriverManager().install(), options=options)
    #webdriver.Chrome.close
    return


if __name__ == '__main__':

    import multiprocessing 

    multiprocessing.set_start_method('spawn', True)
    update_chrome_install() 
    
    sg.theme('LightGreen4')

    T = [[]]
    H = ['Title','URL']
    H1 = ['Title','Domain','Location']

    g_counter = int
    g_test_cnt = int

    base_frame_width = 1024
    search_word_list = []
    frame0 = sg.Frame(' Step.1 ',
        [
            [sg.Text('検索ワード :'), sg.Input(key='-serch-shrimp-') , sg.Button('検索',font=('',11) , key = "-g-search-start-"),  sg.Button('検索終了',font=('',11) , key = "-g-search-break-" ) , sg.Button('決定',font=('',11)) , sg.Text('     ') , sg.Checkbox(': ブラウザ表示', key='-shrimp-cbox-hw-')],
            [sg.Text('連続検索ワード :'), sg.Listbox ( search_word_list , size =(24 , 5) , key='-search-word-list-box-') , sg.Button('追加',font=('',11)),  sg.Button('削除',font=('',11)),sg.Button('リストの読み込み',font=('',11)), sg.Button('リストの保存',font=('',11))],
            [sg.Text('連続検索 :') , sg.Button('検索',font=('',11) , key = "-g-search-words-start-") , sg.Button('検索終了',font=('',11)  , key = "-g-search-words-break-" )],
            [sg.Text('passing :'),sg.Text('', key='-current-text-shrimp-')],
            #検索結果 URL
            [ sg.Table (T , headings=H , auto_size_columns = False , vertical_scroll_only = True ,expand_x=True,
                #def_col_width=32 ,
                col_widths=[45, 38],
                num_rows=9 ,
                display_row_numbers= True ,
                font =('',10) ,
                header_text_color= '#0000ff' ,
                header_background_color= '#cccccc',
                key='-TABLE-'
                ) , sg.Button('CSVを読み込む',font=('',11)), sg.Button('CSVへ保存',font=('',11))] 
            #現在コンタクトフォームの検索結果

        ] , size=(base_frame_width, 332) , key='-frame0-', font=('',14)
    )
    
    T1 = sg.Tab('コンタクトフォーム検索' , 
        [
            [sg.Button('検索開始',font=('',12) ,  key = '-spider-start-'),  sg.Button('検索終了',font=('',11) , key = '-spider-break-' ) , sg.Button('終了')
            , sg.Text('       ') , sg.Spin([1,2,3,4,5,6],initial_value=1 , size=(4,7) , key='-spin-t-cnt-')  , sg.Text(':  起動ブラウザ数') , sg.Text('     ') , sg.Checkbox(': ブラウザ表示', key='-spider-cbox-hw-') ],
            [sg.Text('検出した情報 :', key='-ACT-')],                
            [ sg.Table (T , headings=H1 , auto_size_columns = False , vertical_scroll_only = True ,expand_x=True,     
                col_widths=[45, 20, 40],
                num_rows=9 ,
                display_row_numbers= True ,
                font =('',10) ,
                header_text_color= '#0000ff' ,
                header_background_color= '#cccccc',
                key='-spider-table-')]

        ]
    )

    T2 = sg.Tab('place' , 
        [
            [sg.Text(' 空地 : ') ]
        ]
    )

    TL = [[sg.TabGroup([[T1,T2]]
        , size=(base_frame_width, 240)  , key='-tll-'
    )]]

    frame1 = sg.Frame(' Step.2 ', TL
        , size=(base_frame_width, 240)  , key='-frame1-', font=('',14)
    )

    frame2 = sg.Frame(' Status ',
        [
            [sg.Text('', key='-log-title-' ) , sg.Text('    ', key='-r-space0-') ,  sg.Text('', key='-r-cnt0-') , sg.Text('    ', key='-r-space1-') ,  sg.Text('', key='-r-cnt1-') ],
            [sg.Text('  ', key='-r-space2-') , sg.Text('', key='-r-title0-') ], 
            [sg.Text(''  , key='-r-title1-') , sg.Text('', key='-r-text1-')], 
            [sg.Text('', key='-r-title2-') , sg.Text('', key='-r-text2-')]
        ] , size=(base_frame_width, 120)  , key='-frame2-', font=('',13)
    )

    layout = [
                [frame0] , [frame1] , [frame2] 
            ]

    window = sg.Window('ui_sample_skylli', layout , resizable=True,  finalize=True )
    window["-search-word-list-box-"].bind('<Double-Button-1>' , "+-double click-")  #-Button
    window["-frame0-"].expand(expand_x=True, expand_y=False)
    window["-frame1-"].expand(expand_x=True, expand_y=False)
    window["-frame2-"].expand(expand_x=True, expand_y=False)

    def _search_word_load() :#ファイルからロード
        global search_word_list

        fTyp = [("検索ワードリスト", "*.txt")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        file_name = tk.filedialog.askopenfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):
            f = open(file_name.name , mode="r" , encoding="UTF-8")     
            search_word_list = [] 
            data = f.read()
            for line in data.splitlines():
                search_word_list += [line + '\n']
            f.close()  
            window ['-search-word-list-box-'].Update( search_word_list )
        return

    def _search_word_save() :#ファイルへセーブ
        global search_word_list

        fTyp = [("検索ワードリスト", "*.txt")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        file_name = tk.filedialog.asksaveasfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):
            f = open(file_name.name , mode="w+" , encoding="UTF-8")     
            f.writelines([row for row in search_word_list]) 
            f.close()            

        return

    def _csv_load() :
        global search_result_all

        fTyp = [("CSVファイル", "*.csv")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        #iDir = '../'
        print(f'{id(worker_thread_with)} init thread!' + iDir)
        file_name = tk.filedialog.askopenfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):
            f = open(file_name.name , mode="r" ,newline='', encoding="UTF-8")     
            csvreader = csv.reader(f)
            if csvreader :
                search_result_all = {}
                update_list = list()
                for row in csvreader:
                    search_result_all |= {row[1] : row[0]}
                    update_list += [row]
            f.close()  
            window['-TABLE-'].update(update_list)
        return

    def _csv_save() :
        global search_result_all

        if not search_result_all :
            return

        fTyp = [("CSVファイル", "*.csv")]
        iDir = os.path.abspath(os.path.dirname(__file__))
        file_name = tk.filedialog.asksaveasfile(filetypes=fTyp, initialdir=iDir)
        if None == file_name :
            return 

        if 0 < len(file_name.name):

            f = open(file_name.name , mode="w+" , newline="" , encoding="UTF-8")     
            writer = csv.writer(f)
                            
            update_list = list()
            for key_url , value_title in search_result_all.items():
                update_list += [[value_title , key_url]]

            for row in update_list:
                writer.writerow(row)

            f.close()            

        return


    def shrimp_worker(search_word):
        global go_on
        if not go_on :
            return list()
        
        hw_n = not window['-shrimp-cbox-hw-'].get()
        coshrimp = GoogleShrimp(search_word=search_word , save_file_name="Google検索結果.csv" , breath = shrimp_breather, hedden_window=hw_n) 
        
        return coshrimp.boil() 

    def shrimp_breather(switch , save_file_name="" , param_dic={}, current_text="") : # 戻り値 {}
        global shrimp_stat , search_result_all , go_on
        result = {}
        with __lock:    
            match switch:
                case "breath" :
                    result = {}
                    window['-current-text-shrimp-'].update(current_text)
                case "life" :
                    result = {'life' : go_on}     
    
                case "clean_up" :
                    try:       
                        result = {"clean_up" : False}
                        if param_dic :
                            search_result_all |= param_dic # 

                            update_list = list()
                            for key_url , value_title in search_result_all.items():#その検索ワードの成果だけを表示させたいためparam_dicにしてある
                                update_list += [[value_title , key_url]] # 廃止候補
                            window['-TABLE-'].update(update_list)

                            f_name = save_file_name # ファイルに保存するルーチンは各result格納クラスに移動させる
                            if not f_name :  
                                f_name = "Google検索結果.csv"
                            f = open(f_name , mode="a" , newline="", encoding="UTF-8")     

                            writer = csv.writer(f)
                            
                            for row in update_list:
                                writer.writerow(row)
                            result = {"clean_up" : True}    
                    finally:
                        f.close()
                        shrimp_stat = thread_mode['noop']

        return result

    def window_btn_visible(keys , visible = False): # -serch-shrimp- クリック時に利用できないボタンを無効化　またはその有効化。
        for key in keys :
            window.find_element(key).update(disabled=visible) 

    def frame2_cf_init():
        global g_counter , g_test_cnt
        window["-log-title-"].update(' 検出されたデータ : ') 
        window['-r-title1-'].update(str(' domain : '))
        window['-r-title2-'].update(str(' location : '))
        g_counter = 0 
        g_test_cnt = 0 
    
    def frame2_cf_test_cnt():
        global g_test_cnt , go_on
        g_test_cnt += 1 
        window['-r-cnt1-'].update('    試行回数 : ' + str(g_test_cnt))

    def frame2_cf_s_passing(param_list=list()):
        global g_counter
        if param_list :
            g_counter += 1 
            window["-r-title0-"].update(str(param_list[0])) 
            window['-r-cnt0-'].update('検出数 : ' + str(g_counter))
            window['-r-text1-'].update(str(param_list[1]))
            window['-r-text2-'].update(str(param_list[2]))

    def frame2_cf_s_result():
        global g_counter , g_test_cnt

        window['-r-cnt0-'].update('')
        window['-r-cnt1-'].update('')
        window["-r-title0-"].update('') 
        window['-r-title1-'].update(str(' 試行回数 : '))
        window['-r-title2-'].update(str(' 検出数 : '))
        window['-r-text1-'].update(str(g_test_cnt)) # 
        window['-r-text2-'].update(str(g_counter))


    def spider_worker(url=""):
        global go_on
        if not go_on :
            return list()

        hw_n = not window['-spider-cbox-hw-'].get()
        cospider = CoSpider("ContactForm 検索結果" , url=url , breath=spider_breather , hedden_window=hw_n) 
        cospider.finish_it()
        return cospider.get_result_list()

    def spider_breather(switch , save_file_name="" , param_list=list(), current_text="") : # 戻り値 {}
        global shrimp_stat , search_result_all , go_on
        result = {}
        with __lock:    
            match switch:
                case "breath" :
                    result = {}
                    #window['-CURRENT-TEXT-'].update(current_text)
                case "life" :
                    result = {"life" : go_on}   
    
                case "clean_up" :
                    try:       
                        result = {"clean_up" : False}
                        
                        frame2_cf_s_passing(param_list=param_list)

                        if param_list :

                            f_name = save_file_name
                            if not f_name :  
                                f_name = "eldenring"
                            f = open(f_name + ".csv" , mode="a" , newline="", encoding="UTF-8")                       
                              
                            writer = csv.writer(f)                
                            writer.writerow(param_list)

                            result = {"clean_up" : True}     
                    finally:
                        f.close()
                        shrimp_stat = thread_mode['noop']

        return result



    def skylli_worker_thread_with(swt , param):#ワーカースレッドが終わるまで待ってるスレッド  状態遷移の主軸に
        global worker_thread_with , last_result_object 

        print(f'{id(swt)} skylli_worker_thread_with 354')
        if worker_thread_with is None : #以下の３つ(match)の処理、何れかの一つしか実行できないようにしている。　つもり。            
            return 

        result = ""

        match swt:
            case "swt_shrimp" : 
                if (type(param) is str) and (param) :

                    with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor: 
                        futures.append(executor.submit(shrimp_worker, param)) 
                        for future in concurrent.futures.as_completed(futures):# キューではない
                            result = future.result() #正常終了か問題ありか位は乗せておきたい

                window_btn_visible(shrimp_btn_enable)

            case "swt_shrimps" : 
                if (type(param) is list) and (0 < len(param)) :
                    GS_results =  GoogleShrimp_result()
                    last_result_object = GS_results
                    print(f'{id(last_result_object)} swt_shrimps 373')
                    with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor:   

                        for search_word in param:
                            futures.append(executor.submit(shrimp_worker, search_word))

                        for future in concurrent.futures.as_completed(futures):
                            result = future.result() 

                        #if 2 <= len(result) : #
                        #    GS_results.add_r(title_r_s = result[0] , location_r_s = result[1])

                        #window['-TABLE-'].update(GS_results.get_r_list_table())
                window_btn_visible(shrimps_btn_enable)

            case "swt_spider" : 
                if (type(param) is list) and (0 < len(param)):               
                    #　各クラスに用意してあるレザルトを入れておくインスタンスを作成する
                    CS_result = CoSpider_result() 
                    last_result_object = CS_result # 上書でよい
                    frame2_cf_init()
                    #-spin-t-cnt-
                    m_t = window['-spin-t-cnt-'].get()
                    with ThreadPoolExecutor(max_workers=m_t, initializer=initializer, initargs=('pool',)) as executor:   #ワーカースレッド数
                        for url in param:
                            futures.append(executor.submit(spider_worker, url))
                        
                        for future in concurrent.futures.as_completed(futures): #処理が終わったスレッドが都度検出される。　それの終了待ちループであるようだが この記述で実装されてしまうのは謎だ。
                            result = future.result()

                            frame2_cf_test_cnt() #試行回数をインクリメント
                            with __lock: 
                                if not None == result :#
                                    for item in result:
                                        CS_result.add_r(title_r_s = item[0] , domain_r_s = item[1] , location_r_s = item[2]) #  検索処理の結果を保存しておくオブジェクトを作り、そこに追加していく。

                        # 結果をUIに反映
                        window['-spider-table-'].update(CS_result.get_r_list_table())
                        frame2_cf_s_result()
                window_btn_visible(spider_btn_enable)

        worker_thread_with = None

        return 
        
        # skylli_worker_thread_with end 


    #イベントループ

    futures = []
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == '終了': # スレッドセーフで終了するように main(any time)
            break

        elif event == '-g-search-words-start-':#subthread
            if (shrimp_stat == thread_mode['noop']) and (0 < len(search_word_list)) and (worker_thread_with is None) :
                print(f'{event} init thread!')
                executor = ThreadPoolExecutor(max_workers=1)
                print(f'{id(executor)} init thread!')
                shrimp_stat = thread_mode['active'] 
                
                go_on = True          
                window_btn_visible(shrimps_btn_enable ,visible = True)       
                worker_thread_with = executor.submit(skylli_worker_thread_with , 'swt_shrimps' , search_word_list)
                print(f'{id(worker_thread_with)} init thread!')
             
        elif event == '-g-search-words-break-':#subthread 

            pass

        elif event == '-spider-start-':#subthread   # list からdic に代わってるので動作不可 
            if (0 < len(search_result_all)) and (worker_thread_with is None) :
                executor = ThreadPoolExecutor(max_workers=1)
                url_list = list() 
                for url in search_result_all.keys() :
                    url_list += [url]
                if url_list:
                    spider_stat = thread_mode['active'] 
                    go_on = True
                    window_btn_visible(spider_btn_enable , visible= True)
                    worker_thread_with = executor.submit(skylli_worker_thread_with , 'swt_spider' , url_list)

        elif event == '-g-search-start-': # 検索
            if (shrimp_stat == thread_mode['noop'] )  and (worker_thread_with is None) :
                s_str =  window['-serch-shrimp-'].get()
                if s_str : #スペースだろうが検索する 正規化はしない
                    executor = ThreadPoolExecutor(max_workers=1)
                    shrimp_stat = thread_mode['active'] 
                    go_on = True                     
                    
                    window_btn_visible(shrimp_btn_enable ,visible = True)    
                    worker_thread_with = executor.submit(skylli_worker_thread_with , 'swt_shrimp' , s_str)
                
        elif event == '-g-search-break-': # 検索終了 main(any time)
            if shrimp_stat == thread_mode['active'] :
                go_on = False #スレッドの処理を終了を促す
                shrimp_executor = None
                shrimp_stat = thread_mode['noop']  #back to noop

        elif event == '追加': #main(any time)
            w = sg . PopupGetText ('検索ワード ' , title = '検索ワードリストへ追加')
            if w:
                search_word_list += [w + '\n']
                window ['-search-word-list-box-']. Update ( search_word_list )

        elif event == '削除': #main(any time)
            if values['-search-word-list-box-']:
                search_word_list.remove(values['-search-word-list-box-'][0]) 
                window ['-search-word-list-box-'].Update( search_word_list )


        elif event == 'リストの読み込み': #main(any time)
            _search_word_load()
            window ['-search-word-list-box-'].Update( search_word_list )

        elif event == 'リストの保存': #main(any time)
            _search_word_save()

        elif event == 'CSVを読み込む': #main(any time)
            _csv_load()

        elif event == 'CSVへ保存': #main(any time)
            _csv_save()


        elif event == '-search-word-list-box-+-double click-': #main(any time)
            if values['-search-word-list-box-']:
                val = values['-search-word-list-box-'][0] 
                window ['-serch-shrimp-'].Update(val)


        elif event == '-spider-break-': #main(any time)   spider terminate
            window.refresh()
            go_on = False


        elif event == '決定':
            window_btn_visible(shrimps_btn_enable ,visible = True)
         
            #sg.preview_all_look_and_feel_themes()

    window.close()

    exit()
    
    #Co_spider テスト
    u0 = "https://wx10.wadax.ne.jp/~yoshidakaya-co-jp/" 
    #url = "https://www.octoparse.jp/"
    u1 = "https://oec-evaluation.uh-oh.jp/"
    u2 = "https://bonten.cc/"
    u3 = "https://akubi-office.com/"
    u4 = 'https://kokusai-bs.jp/' 
    u5 = "https://exceed-confect.co.jp/"

    target_list = [u0 , u2, u3, u3, u4 ,u5]

    futures = []

    #ProcessPoolExecutor   破棄
    with ThreadPoolExecutor(max_workers=1, initializer=initializer, initargs=('pool',)) as executor:       

        for url in target_list:
            futures.append(executor.submit(worker, url))

        #for future in as_completed(futures):
        #    r_list = list(future.result()) 


        if futures :
            try:       
                f = open("nioh" + ".csv" , mode="a" , newline="", encoding="UTF-8")           
                for ft in futures :
                    r_list = list(ft.result())
                    if r_list :
                    # 排他的になってない 
                        writer = csv.writer(f)
                        writer.writerow(r_list)
            finally:
                f.close()

        #sg.theme_previewer()


