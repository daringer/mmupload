from subprocess import getoutput as run

from selenium import webdriver as drv
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.keys import Keys

from time import sleep

run("echo '123456' > /tmp/dummy.txt")

opts = ChromeOptions()
br = drv.Chrome(chrome_options=opts)

br.get("http://test:test@localhost:5001")
br.get("http://test:test@localhost:5001/dir")
sleep(1)
br.get("http://test:test@localhost:5001/dir/files")
sleep(1)
br.get("http://test:test@localhost:5001/dir/pastebin")
sleep(1)
br.get("http://test:test@localhost:5001/pastebin")
sleep(1)
br.get("http://test:test@localhost:5001")
sleep(1)

el = br.find_element_by_name("new_dirname")

el.send_keys("yes_test")
#el.send_keys(Keys.RETURN)

print("el.find_elements_by_tag_name(\"what\").find_element_by_value(\"create\")")

sleep(1)

for el in br.find_elements_by_name("what"):
    print (el.get_attribute("value"))
    sleep(1)
    if el.get_attribute("value") == "create":
        el.click()





#y.send_keys("Am Laubersberg")
#y.send_keys(Keys.RETURN)
#button = br.find_element_by_name("mm_mon")



#br.find_elements_by_name
#day.find_element_by_tag_name
#br.find_element_by_id
#s

