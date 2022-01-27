import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.common import exceptions
import time
import datetime
import pickle

DATE_FORMAT = "%B %d, %Y %I:%M %p"


class RetrievalError(Exception):
    pass


class Post:
    def __init__(self, old_url, data=None):
        self.old_url = old_url
        self.new_url = ""
        self.data = self.get_post() if not data else data

    @staticmethod
    def get_title_and_featured_img(header):
        title = header.find(
            "h1", class_="elementor-heading-title elementor-size-default"
        ).text.strip()

        try:
            featured_img = header.find("img").attrs["src"]
        except AttributeError:  # no image
            featured_img = None

        return title, featured_img

    @staticmethod
    def get_author(soup):
        return soup.find(
            "span",
            class_="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-author",
        ).text.strip()

    @staticmethod
    def get_date(soup):
        pub_date = soup.find(
            "span",
            class_="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-date",
        ).text.strip()

        pub_time = (
            soup.find(
                "span",
                class_="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-time",
            )
            .text.strip()
            .upper()
        )

        return datetime.datetime.strptime(f"{pub_date} {pub_time}", DATE_FORMAT)

    @staticmethod
    def get_featured_img(header):
        try:
            return header.find("img").attrs["src"]
        except AttributeError:  # no image
            return None

    @staticmethod
    def get_tags(soup):
        return [
            tag.text.lower()
            for tag in soup.find("div", class_="tagcloud").find_all("a")
        ]

    def get_post(self):
        r = requests.get(self.old_url)

        soup = BeautifulSoup(r.content, "html5lib")

        table = soup.find("div", class_="elementor-text-editor elementor-clearfix")

        header = soup.find_all("div", class_="elementor-widget-wrap")[1]

        title, featured_img = self.get_title_and_featured_img(header)
        author = self.get_author(soup)
        date = self.get_date(soup)
        featured_img = self.get_featured_img(header)
        content = table.prettify()
        tags = self.get_tags(soup)

        data = {
            "title": title,
            "author": author,
            "featured_img": featured_img,
            "date": date,
            "content": content,
            "tags": tags,
        }

        with open("logs.txt", "a") as f:
            log_str = "Retrieving old blog post...\n\n"
            for k, v in data.items():
                if k != "content":
                    log_str += f"{k.title()}: {v}\n\n"
            log_str += "Retrieval successful!\n\n*********************\n\n"
            f.write(log_str)

        return data

    def create_post(self, driver):
        if not self.data:
            raise RetrievalError(
                "This post contains incomplete data - please get its data and try again."
            )

        driver.find_element_by_xpath(
            "/html/body/main/section/div/p[1]/a"
        ).click()  # xpath to "Add Post" button

        secondary_driver = driver.switch_to.active_element

        time.sleep(2)

        secondary_driver.find_element_by_xpath(
            "/html/body/main/section/div/form/div[2]/div[2]/div[1]/ul/li[2]/label"
        ).click()  # xpath to "Published" selector

        secondary_driver.find_element_by_xpath(
            "/html/body/main/section/div/form/div[2]/div[1]/div[1]/div[1]/div/div[1]/div/div[2]/div/div/div/div[6]/div/div[2]/button"
        ).click()  # xpath to '< >' button for source code

        time.sleep(1)

        # Title

        title_box = secondary_driver.find_element_by_xpath(
            "/html/body/main/section/div/form/div[1]/input"
        )
        title_box.send_keys(self.data["title"])

        # Content

        content_box = secondary_driver.find_element_by_xpath(
            "/html/body/div[7]/div/div[2]/div[2]/div/textarea"
        )
        content_box.send_keys(self.data["content"])

        secondary_driver.find_element_by_xpath(
            "/html/body/div[7]/div/div[3]/div/div[2]/button"
        ).click()  # xpath to "Ok" button

        time.sleep(1)

        # Author

        author_menu = Select(
            secondary_driver.find_element_by_xpath(
                "/html/body/main/section/div/form/div[2]/div[2]/div[7]/select"
            )
        )

        author_found = False
        try:
            author_menu.select_by_visible_text(self.data["author"])
        except exceptions.NoSuchElementException:
            author_menu.select_by_visible_text("JewishGen Team")
            author_found = False
        else:
            author_found = True
        finally:
            with open("logs.txt", "a") as f:
                log_str = "Posting to new blog...\n\n"
                for k, v in self.data.items():
                    if k != "content":
                        if k == "author" and not author_found:
                            log_str += (
                                f"ATTENTION REQUIRED: {v} not found in authors list on new blog - JewishGen"
                                f" Team has been set as the author.\n\n"
                            )
                        else:
                            log_str += f"{k.title()}: {v}\n\n"
                f.write(log_str)

        # Tags

        tag_options = secondary_driver.find_element_by_xpath(
            "/html/body/main/section/div/form/div[2]/div[2]/div[8]/ul"
        ).find_elements_by_tag_name("li")

        for tag_option in tag_options:
            label = tag_option.find_element_by_tag_name("label").text

            if label.lower() in self.data["tags"]:
                tag_option.find_element_by_tag_name(
                    "label"
                ).click()  # if the tag name matches, click it

        # Date

        # Gets to correct month and year
        driver.find_element_by_xpath(
            "/html/body/main/section/div/form/div[2]/div[2]/div[2]/div/input"
        ).click()

        driver.implicitly_wait(1)

        secondary_driver = driver.switch_to.active_element

        month_menu = Select(
            secondary_driver.find_element_by_xpath(
                "/html/body/div[5]/div[1]/div/div/select"
            )
        )

        month_menu.select_by_value(str(self.data["date"].month - 1))

        year_menu = secondary_driver.find_element_by_xpath(
            "/html/body/div[5]/div[1]/div/div/div/input"
        )

        year_menu.click()
        year_menu.clear()
        year_menu.send_keys(self.data["date"].year)

        # Then clicks on the tag with the date as self.data['date']
        days = secondary_driver.find_element_by_xpath(
            "/html/body/div[5]/div[2]/div/div[2]/div"
        ).find_elements_by_class_name("flatpickr-day ")

        for day in days:
            if (
                datetime.datetime.strptime(
                    day.get_attribute("aria-label"), DATE_FORMAT
                ).date()
                == self.data["date"].date()
            ):
                day.click()
                break
        else:
            print(
                f"Could not set the date...publication date is today, {datetime.date.today()}."
            )
            with open("logs.txt", "a") as f:
                f.write(
                    f"ATTENTION REQUIRED: Date could not be determined - publication date has been set as today,"
                    f" {datetime.date.today()}.\n\n"
                )

        # Time

        hour_input = secondary_driver.find_element_by_xpath(
            "/html/body/div[5]/div[3]/div[1]/input"
        )

        hour_input.click()
        hour_input.clear()
        hour_input.send_keys(self.data["date"].hour)

        minute_input = secondary_driver.find_element_by_xpath(
            "/html/body/div[5]/div[3]/div[2]/input"
        )

        minute_input.click()
        minute_input.clear()
        minute_input.send_keys(self.data["date"].minute)

        secondary_driver.find_element_by_xpath(
            "/html/body/div[5]/div[4]"
        ).click()  # clicks done

        return self.publish_post(driver)

    def publish_post(self, driver):
        time.sleep(1)

        self.new_url = driver.find_element_by_xpath(
            "/html/body/main/section/div/form/div[2]/div[2]/div[10]/input"
        ).get_attribute("value")

        driver.find_element_by_xpath(
            "/html/body/main/section/div/form/div[2]/div[1]/div[2]/input"
        ).click()  # xpath to "Save Post" button

        with open("logs.txt", "a") as f:
            f.write(
                f'Posting successful!\n\n{self.data["title"]} has been successfully migrated from {self.old_url} to {self.new_url}.\n\n*********************\n\n'
            )

        return driver

    def __str__(self):
        out_str = f"This is an instance of a Post object, whose original URL is {self.old_url}"

        if self.new_url:
            out_str += f" and whose new URL is {self.new_url}."
        else:
            out_str += ". The post has not been migrated yet.\n\n"

        out_str += "The Post contains the following data:\n\n"

        for k, v in self.data.items():
            if k != "content":
                out_str += f"- {k.title()} -- {v}\n"

        out_str += "\n"

        return out_str

    def __add__(self, other):
        """
        Ex:

        z = x + y --> x.__add__(y)

        Post z has all of the data of x, EXCEPT that the content of y is appended to the content of x.

        x and y remain unchanged.

        :param other: another Post object
        :type: Post
        :return: a new Post object whose content is the combination of self and other's content
        """
        if isinstance(other, Post):
            data = self.data

            data["content"] += f'\n\n{other.data["content"]}'

            return Post(self.old_url, data)
        else:
            raise ArithmeticError("You cannot add a Post object and another object.")


def login(driver):
    email = input("Please input your email: ")
    password = input("Please input your password: ")

    driver.find_element_by_xpath(
        "/html/body/main/section/div/div/div/form/div[1]/input"
    ).send_keys(email)
    driver.find_element_by_xpath(
        "/html/body/main/section/div/div/div/form/div[2]/input"
    ).send_keys(password)
    driver.find_element_by_xpath(
        "/html/body/main/section/div/div/div/form/button"
    ).click()

    driver.implicitly_wait(2)


def load_existing_post_list():
    return pickle.load(open("posts_list.pickle", "rb"))


if __name__ == "__main__":
    start = time.time()
    posts = load_existing_post_list()

    BLOG_MAIN_URL = input("What is the URL for the blog? ")
    WEBDRIVER_PATH = input("Where is the webdriver located? ")

    driver = webdriver.Chrome(WEBDRIVER_PATH)
    driver.get(BLOG_MAIN_URL)
    login(driver)

    num_posts = len(posts)
    print(f"Initiating migration of {num_posts} posts now...")
    i = 0

    for post in posts:
        print("Creating a new post!")
        driver.get(BLOG_MAIN_URL)
        driver = post.create_post(driver)
        print("Success! Moving to next url...")
        i += 1
        print(f"Retrieval: {(i / num_posts) * 100}% done")

    driver.implicitly_wait(2)
    driver.close()

    with open("logs.txt", "a") as f:
        f.write(
            "\n\n\n\n*********************\n*********************\n*********************\n\n\nMigration complete.\n"
        )

    print(f"\n\n\nMigration complete.\n\nTime elapsed: {time.time() - start} s")
