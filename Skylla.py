import os
import urllib.parse
import time
import PySimpleGUI as sg
import csv

#UI 機能統合など
from threading import Lock
#from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver 

from Co_Spider import CoSpider 



__lock = Lock()
go_on = True

def initializer(string):
    print(f'{string} init thread!')


def worker(url):
    cs = CoSpider("nioh" , url=url , breath=breather , hedden_window=False) 
    cs.finish_it()
    return cs.get_result_list()


def breather(switch , save_file_name="" , param_list=list()) : # 戻り値 {}
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
                        f_name = "nioh.csv"
                    f = open(f_name , mode="a" , newline="", encoding="UTF-8")       
                    if param_list :
                        writer = csv.writer(f)
                        writer.writerow(param_list)
                finally:
                    f.close()

                result = {}

    return result


def update_chrome_install() :
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    webdriver.Chrome(ChromeDriverManager().install(), options=options)
    webdriver.Chrome.close
    return

if __name__ == '__main__':

    import multiprocessing 

    multiprocessing.set_start_method('spawn', True)
    update_chrome_install() 
    


    sg.theme('LightBrown6')

    frame1 = sg.Frame('',
    [
        [sg.Text('検索ワード :'), sg.Input(key='-seach-') , sg.Button('検索'), sg.Button('終了')],
        [sg.Listbox(values=sg.theme_list(), size=(20, 9), key='-LIST-', enable_events=True)]
    ] , size=(540, 280) 
    )

    frame2 = sg.Frame('',
    [
                [sg.Text('', key='-ACT-')],
                [sg.Button('決定'), sg.Button('終了')]
    ] , size=(540, 280) 
    )

    frame3 = sg.Frame('',
    [
        [sg.Multiline(default_text='',size=(160,9), border_width=2, key='memo')]
    ] , size=(540, 160) 
    )

    layout = [
                [frame1] , [frame2] , [frame3]
            ]

    window = sg.Window('sample', layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == '終了':
            break
        if event == '決定':
            window['-ACT-'].update(f'成功！ あなたの名前は{values["-NAME-"]}さんですね')

    window.close()


    exit()
    

    u0 = "https://wx10.wadax.ne.jp/~yoshidakaya-co-jp/" 
    #url = "https://www.octoparse.jp/"
    u1 = "https://oec-evaluation.uh-oh.jp/"
    u2 = "https://bonten.cc/"
    u3 = "https://akubi-office.com/"
    u4 = 'https://kokusai-bs.jp/' 
    u5 = "https://exceed-confect.co.jp/"

    target_list = [u0 , u2, u3, u3, u4 ,u5]

    futures = []
    #ProcessPoolExecutor
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


