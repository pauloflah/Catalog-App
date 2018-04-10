from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy_utils import database_exists, drop_database, create_database

from database_setup import CategoryList, CategoryItem, Profile, Base

engine = create_engine('sqlite:///itemcatalog.db')

# Clear database
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Create dummy user
user1 = User(name="Robo Barista", email="tinnyTim@udacity.com")
session.add(user1)
session.commit()

# Menu for UrbanBurger
category1 = CategoryList(name="Urban Burger", user_id=1)

session.add(category1)
session.commit()

item1 = CategoryItem(name="Veggie Burger",
                     description="Juicy grilled veggie patty with " +
                                 "tomato mayo and lettuce",
                     user_id=1, category=category1)

session.add(item1)
session.commit()

item2 = CategoryItem(name="French Fries",
                     description="with garlic and parmesan",
                     user_id=1, category=category1)

session.add(item2)
session.commit()

item3 = CategoryItem(name="Chicken Burger",
                     description="Juicy grilled chicken patty with " +
                                 "tomato mayo and lettuce",
                     user_id=1, category=category1)

session.add(item3)
session.commit()

item4 = CategoryItem(name="Chocolate Cake",
                     description="fresh baked and served with ice cream",
                     user_id=1, category=category1)

session.add(item4)
session.commit()

item5 = CategoryItem(name="Sirloin Burger",
                     description="Made with grade A beef",
                     user_id=1, category=category1)

session.add(item5)
session.commit()

item6 = CategoryItem(
    name="Root Beer", description="16oz of refreshing goodness",
    user_id=1, category=category1)

session.add(item6)
session.commit()

item7 = CategoryItem(name="Iced Tea", description="with Lemon",
                     user_id=1, category=category1)

session.add(item7)
session.commit()

item8 = CategoryItem(name="Grilled Cheese Sandwich",
                     description="On texas toast with American Cheese",
                     user_id=1, category=category1)

session.add(item8)
session.commit()

categories = session.query(Category).all()
for category in categories:
    print "Category: " + category.name
