#!/usr/bin/python
import logging
import os
import sqlite3
import secrets_precios
from datetime import datetime

from telegram import Update
from telegram import InlineKeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
# IMPORTANT: Replace with your actual Telegram Bot Token
# You can get this from BotFather on Telegram.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', secrets_precios.TELEGRAM_TOKEN)

# SQLite Database File
DB_FILE = 'products.db'

conversation_action = []

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    #format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR
)
logger = logging.getLogger(__name__)

# --- Database Initialization ---
def init_db():
    """Initializes the SQLite database, creating tables if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create products table
        # 'name' is UNIQUE to ensure each product is stored once by its name
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id_prod INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                photo TEXT,
                d_created TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id_precio INTEGER PRIMARY KEY AUTOINCREMENT,
                id_prod INTEGER,
                id_com INTEGER,
                last_price REAL NOT NULL,
                d_created TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business (
                id_com INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                d_created TEXT NOT NULL
            )
        ''')

        conn.commit()
        logger.info(f"SQLite database '{DB_FILE}' initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing SQLite database: {e}", exc_info=True)
        # Re-raise the exception or exit if database initialization fails
        raise
    finally:
        if conn:
            conn.close()

# Initialize the database when the script starts
try:
    init_db()
except Exception as e:
    logger.error("Failed to initialize database, exiting.")
    exit(1)


# --- Utility Functions ---
# Note: The slugify function is no longer strictly needed for database keys
# since we're using auto-incrementing IDs and the 'name' field directly.
# However, it's kept as a general utility, though not used in the current DB logic.
def slugify(text):
    """Converts a string into a URL-friendly slug. Not used for DB IDs in SQLite setup."""
    text = text.lower()
    text = text.replace(" ", "-")
    text = "".join(c for c in text if c.isalnum() or c == '-')
    return text

# --- Telegram Bot Commands ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#    await update.message.reply_text(f'Hello {update.effective_user.first_name}')
    """Sends a welcome message and explains how to use the bot."""
    user = update.effective_user
    if 'business' in context.user_data:
        await update.message.reply_html(
            f"Hi {user.mention_html()}! 👋\n"
            "I will help you manage product prices.\n"
            "Your current business is set to: " + context.user_data['business'] + "\n\n"
        )
    else:
        #await query.message.reply_text(
        await update.message.reply_html(
            f"Hi {user.mention_html()}! 👋\n"
            "I will help you manage product prices.\n\n" \
            "List Business: /lb [name]\n" \
            "List Products: /lp [name]\n" \
            "List Product price: /lpp [name]\n"
        )   


async def add_business(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a new business in SQLite."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "🛑 Invalid format. Please use: `/ab <business_name> <place>`\n"
            "Example: `/ab dia constituyentes`"
        )
        return

    conn = None
    try:
        business_name = " ".join(args).strip()

        if not business_name:
            await update.message.reply_text("🛑 Business name cannot be empty.")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        current_time_str = datetime.now().isoformat() # ISO 8601 format for TEXT storage

        # Check if product exists by name
        cursor.execute("SELECT id_com FROM business WHERE name = ?", (business_name,))
        business_row = cursor.fetchone()

        if business_row:
            # Commerce exists, update the latest price
            business_id = business_row[0]
            await update.message.reply_text(
                f"✅ Found this business in mydata: '{business_name}'."
            )

        # Business does not exist, insert a new one
        sql = ''' INSERT INTO business (name, d_created) VALUES (?, ?) '''
        print(f"INSERT INTO business (name, d_created) VALUES ({business_name}, {current_time_str})")
        cursor.execute(sql,  (business_name, current_time_str))
        conn.commit()
        business_id = cursor.lastrowid # Get the ID of the newly inserted product
        await update.message.reply_text(
            f"✨ Added new business '{business_name}' (ID: {business_id})."
        )
        logger.info(f"Added new business '{business_name}' (ID: {business_id}).")

    except sqlite3.IntegrityError as e:
        # This handles cases where, for example, a UNIQUE constraint is violated
        logger.error(f"SQLite Integrity Error: {e}", exc_info=True)
        await update.message.reply_text(
            "An integrity error occurred (e.g., duplicate business name). Please check your input."
        )
    except sqlite3.Error as e:
        logger.error(f"SQLite database error: {e}", exc_info=True)
        await update.message.reply_text(
            "A database error occurred while trying to add the business. Please try again later."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        await update.message.reply_text(
            "An unexpected error occurred. Please try again later."
        )
    finally:
        if conn:
            conn.close()



async def update_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Add or update a product price. """
    #args = context.args
    #price = float(args[-1])
    #if price <= 0:
    #    await update.message.reply_text("🛑 Price must be a positive number.")
    #    return
    # To manage conversation:
    conversation_action.append('setprice')
    if 'business' not in context.user_data:
        await update.message.reply_html(
            f"Please set a business for the product.\n"
            "Use /lb and select one.\n\n"
        )
        return
    if 'product' not in context.user_data:
        await update.message.reply_html(
            f"Please select a product to modify its price..\n"
            "Use /lp and select one.\n\n"
        )
        return
    #conn = None
    #conn = sqlite3.connect(DB_FILE)
    #cursor = conn.cursor()
    #sql = "select name from products where id_prod = ?"
    #cursor.execute(sql, (context.user_data['product'],))
    #products = cursor.fetchone()
    id_prod = context.user_data['product']
    id_com = context.user_data['business']
    bn = context.user_data['business_name']
    pn = context.user_data['product_name']
    #sql = "SELECT name FROM business where id_com = ?"
    #cursor.execute(sql, (id_com,))
    #business_name = cursor.fetchone()
    await update.message.reply_html(
    f"All right.  You are at {bn}, which is the price for: {pn}?\n\n"
    )
    #conn.close()



async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Adds a new product or updates an existing product's price in SQLite.
    The product is added to the selected business.  If no specific business
    is select it should not leave to add it.    
    """
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "🛑 Invalid format. Please use: `/ap <product_name>`\n"
            "Example: `/ap Apple Juice`"
        )
        return

    conn = None
    try:
        product_name = " ".join(args).strip()

        if not product_name:
            await update.message.reply_text("🛑 Product name cannot be empty.")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        current_time_str = datetime.now().isoformat() # ISO 8601 format for TEXT storage

        # Check if product exists by name
        cursor.execute("SELECT id_prod FROM products WHERE name = ?", (product_name,))
        product_row = cursor.fetchone()

        if product_row:
            # Product exists, update the latest price
            product_id = product_row[0]
            await update.message.reply_text(
                f"✅ Encontre ese producto en mis datos: '{product_name}'.\n"
                "Seleccione el producto para actualizar el precio.\n"
            )
            return

        # Product does not exist, insert a new one
        print(f"INSERT INTO products (name, d_created) VALUES ({product_name}, {current_time_str})")
        cursor.execute(
            "INSERT INTO products (name, d_created) VALUES (?, ?)",
            (product_name, current_time_str)
        )
        product_id = cursor.lastrowid # Get the ID of the newly inserted product
        conn.commit()
        await update.message.reply_text(
            f"✨ Added new product '{product_name}'."
        )
        logger.info(f"Added new product '{product_name}' (ID: {product_id}).")

    except sqlite3.IntegrityError as e:
        # This handles cases where, for example, a UNIQUE constraint is violated
        logger.error(f"SQLite Integrity Error: {e}", exc_info=True)
        await update.message.reply_text(
            "An integrity error occurred (e.g., duplicate product name). Please check your input."
        )
    except sqlite3.Error as e:
        logger.error(f"SQLite database error: {e}", exc_info=True)
        await update.message.reply_text(
            "A database error occurred while trying to add the product. Please try again later."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        await update.message.reply_text(
            "An unexpected error occurred. Please try again later."
        )
    finally:
        if conn:
            conn.close()


async def list_business(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all business and their latest prices from SQLite."""
    args = context.args
    """ Check if there is an argument, if it does it is a business name string/substring to search """
    conn = None
    try:
        sql = "SELECT id_com, name FROM business ORDER BY name ASC"
        business_substring = ""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        if len(args) > 0:
            business_substring = args[-1]
            #sql = "SELECT id, name, description FROM products WHERE name LIKE ?"
            sql = "SELECT id_com, name FROM business where name like ? ORDER BY name ASC"
            logger.info("List business with string.")
            cursor.execute(sql, ('%' + business_substring + '%',))
        else:
            logger.info("List Business")
            cursor.execute(sql)
        #cursor.execute("SELECT id_com, name FROM business ORDER BY name ASC")
        businesses = cursor.fetchall()
        
        commerce_list_text = "📊 **Your Tracked Business/es:**\n\n"
        commerce_found = False
        keyboard = []
        for business_id, commerce_name in businesses:
            keyboard.append([InlineKeyboardButton(commerce_name, callback_data="set_business_"+ str(business_id))])
            commerce_found = True
        """Sends a message with an inline keyboard to choose a mood."""
        reply_markup = InlineKeyboardMarkup(keyboard)

        if not commerce_found:
            commerce_list_text = "Empty 🥺\n" \
            "No commerce tracked yet. Use `/ic <commerce_name> <location>` to add one!"
        await update.message.reply_text(
            "Choose your the place where you want to check:",
            reply_markup=reply_markup
        )
        #await update.message.reply_text(commerce_list_text, parse_mode='Markdown')
        logger.info("Listed all commerces from SQLite.")

    except sqlite3.Error as e:
        logger.error(f"SQLite database error during list: {e}", exc_info=True)
        await update.message.reply_text(
        "A database error occurred while trying to retrieve the product list. Please try again later."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during list: {e}", exc_info=True)
        await update.message.reply_text(
        "An unexpected error occurred while listing products. Please try again later."
        )
    finally:
        if conn:
            conn.close()


async def update_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    args = context.args
    if 'product' in context.user_data:
        await update.message.reply_html(
        f"Product is set to: {context.user_data['product_name']}.  Enter the new name:\n"
        )
        context.user_data['rename'] = context.user_data['product']


async def list_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all products with a given substring name."""
    args = context.args
    conn = None
    try:
        # This is the query to bring the products and their prices
        # But these need to exist already.  This query will probably be
        # used with the /lpp command (list product prices) where i am in a 
        # specific business or look for prices of a product business wide.

        sql = "select p.id_prod, p.name, i.last_price, " \
        "cast (JULIANDAY(datetime()) - JULIANDAY(i.d_created) as integer) as days, " \
        "b.name from " \
        "products p LEFT JOIN prices i " \
        "ON i.id_prod = p.id_prod " \
        "INNER JOIN business b " \
        "ON i.id_com = b.id_com " \
        "where (p.id_prod, i.d_created, b.id_com) in(" \
        "    select id_prod, max(d_created), id_com from prices" \
        "    group by id_prod, id_com" \
        ")" \
        "order by days asc, i.last_price asc;"
        product_substring = ""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        if len(args) > 0:
            product_substring = args[-1]
            sql = "select p.id_prod, p.name, i.last_price, " \
            "cast (JULIANDAY(datetime()) - JULIANDAY(i.d_created) as integer) as days, " \
            "b.name from " \
            "products p LEFT JOIN prices i " \
            "ON i.id_prod = p.id_prod " \
            "INNER JOIN business b " \
            "ON i.id_com = b.id_com " \
            "and lower(p.name) like ? " \
            "where (p.id_prod, i.d_created, b.id_com) in(" \
            "    select id_prod, max(d_created), id_com from prices" \
            "    group by id_prod, id_com" \
            ")" \
            "order by days asc, i.last_price asc;"
            logger.info("List Products with string.")
            cursor.execute(sql, ('%' + product_substring + '%',))
        else:
            logger.info("List Products")
            cursor.execute(sql)
        products = cursor.fetchall()
        product_list_text = "📊 **Your Tracked Products:**\n\n"
        products_found = False

        keyboard = []
        for product_id, product_name, price, sincedays, business_name in products:
            keyboard.append([InlineKeyboardButton(product_name + ", $ " + str(price) + " [" + str(sincedays) + "] in " + business_name, callback_data="set_prod_"+ str(product_id))])
            products_found = True
        reply_markup = InlineKeyboardMarkup(keyboard)

        if not products_found:
            commerce_list_text = "Empty 🥺\n" \
            "No products tracked yet. Use `/ap <Product Name>` to add one!"
        await update.message.reply_text(
            "Choose a product:",
            reply_markup=reply_markup
        )
    except sqlite3.Error as e:
        logger.error(f"SQLite database error during list: {e}", exc_info=True)
        await update.message.reply_text(
            "A database error occurred while trying to retrieve the product list. Please try again later."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during list: {e}", exc_info=True)
        await update.message.reply_text(
            "An unexpected error occurred while listing products. Please try again later."
        )
    finally:
        if conn:
            conn.close()


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all products with a given substring name."""
    args = context.args
    conn = None
    try:
        sql = "select id_prod, name from products"
        product_substring = ""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        if len(args) > 0:
            product_substring = args[-1]
            sql = "select id_prod, name from products where name like ?"
            logger.info("List Products with string.")
            cursor.execute(sql, ('%' + product_substring + '%',))
        else:
            logger.info("List Products")
            cursor.execute(sql)
        products = cursor.fetchall()
        product_list_text = "📊 **Your Tracked Products:**\n\n"
        products_found = False

        keyboard = []
        #for product_id, product_name, price, sincedays, business_name in products:
        #    keyboard.append([InlineKeyboardButton(product_name + ", $ " + str(price) + " [" + str(sincedays) + "] in " + business_name, callback_data="set_prod_"+ str(product_id))])
        #    products_found = True
        for product_id, product_name in products:
            keyboard.append([InlineKeyboardButton(product_name, callback_data="set_prod_"+ str(product_id))])
            products_found = True
        reply_markup = InlineKeyboardMarkup(keyboard)

        if products_found:
            await update.message.reply_text(
            "Choose a product:",
            reply_markup=reply_markup)
        else:
            await update.message.reply_text(
            "Empty 🥺\nNo products found. Use `/ap <product name>` to add one!"
            )
#        await update.message.reply_text(product_list_text, parse_mode='Markdown')
#        logger.info("Listed all products from SQLite.")
    except sqlite3.Error as e:
        logger.error(f"SQLite database error during list: {e}", exc_info=True)
        await update.message.reply_text(
            "A database error occurred while trying to retrieve the product list. Please try again later."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during list: {e}", exc_info=True)
        await update.message.reply_text(
            "An unexpected error occurred while listing products. Please try again later."
        )
    finally:
        if conn:
            conn.close()



async def set_agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer() # Acknowledge the callback
    callback_data = query.data #
    conn = None
    logger.debug(f"Entering set_agent_callback with {callback_data}")
    if callback_data.startswith("set_business_"):
        business_id = callback_data.replace("set_business_", "")
        context.user_data['business'] = business_id

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        sql = "SELECT name FROM business where id_com = ?"
        cursor.execute(sql, (context.user_data['business'],))
        business_name = cursor.fetchone()
        context.user_data['business_name'] = business_name[0]
        bn = context.user_data['business_name']
        logger.debug(f"Selected a business id: {business_id}")
        # There was a product selected before,only business set was pending:
        if 'product' in context.user_data:
            pn = context.user_data['product_name']
            # The user wanted to modify the price, selected a business, product was pending:
            if 'setprice' in conversation_action:
                await query.edit_message_text(
                f"Your business has been set to: " + bn + "! 😊\n" \
                "Product is set to: " + pn + ".\nEnter the price:\n"
                )
        else:
            await query.edit_message_text(
            f"Your business has been set to: " + bn + "! 😊\n" \
            "Commands:\n" \
            "List Products: /lp [string]\n" \
            "Product Prices: /lpp [string]\n" \
            "Add product: /ap <name>\n"
            )
    elif callback_data.startswith("set_prod_"):
        prod_id = callback_data.replace("set_prod_", "")
        context.user_data['product'] = prod_id
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            sql = "select name from products where id_prod = ?"
            logger.warning(f"select name from products where id_prod = {prod_id}")
            cursor.execute(sql, (prod_id,))
            products = cursor.fetchone()
            context.user_data['product_name'] = products[0]
            pn = products[0]
            if 'business' not in context.user_data:
                await query.message.reply_text(
                f"You selected: {pn}.\n" \
                "Select a business: /lb [name]\n" \
                "Modify product name: /mp\n" \
                "Type /h for more commands.")
            else:
                bn = context.user_data['business_name']
                await query.edit_message_text(
                f"You selected: {pn}, business is: {bn}\n" \
                "To set the price: /up\n" \
                "To rename it: /mp\n" \
                "List products /lp [name]"
                )
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            await query.message.reply_text(
                "An unexpected error occurred. Please try again later."
            )
        finally:
            if conn:
                conn.close()
    else:
        await query.edit_message_text("An unknown button was pressed.")



async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Check if we are waiting for something in particular, else
    Responds to unknown commands."""
    logger.info(f"a text was received that is not a specific command")
    conn = None
    if 'rename' in context.user_data:
        id_prod = context.user_data['rename']
        logger.info(f"Wants to rename the product{id_prod}")
        del context.user_data['rename']
        try:
            product_name =  update.message.text
            await update.message.reply_text(
                f"The product name is set to {product_name}"
            )
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            sql = ''' update products set name = ? where id_prod = ? '''
            print(f"update products set name = ? where id_prod = ?\n" \
            "VALUES({product_name},{id_prod})")
            cursor.execute(sql,  (product_name, id_prod))
            conn.commit()  
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            await update.message.reply_text(
                "An unexpected error occurred. Please try again later."
            )
        finally:
            if conn:
                conn.close()
    elif 'setprice' in conversation_action :
        #'business' in context.user_data and 'product' in context.user_data:
        try:
            product_price = update.message.text
            await update.message.reply_text(
                f"The price for the product is set to {product_price}"
            )
            id_prod = context.user_data['product']
            id_com = context.user_data['business']
            current_time_str = datetime.now().isoformat() # ISO 8601 format for TEXT storage
            # doing here the insert of the new product price for this business.
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            sql = ''' INSERT INTO prices (id_prod, id_com, last_price, d_created) VALUES (?, ?, ?, ?) '''
            print(f"INSERT INTO prices (id_prod, id_com, last_price, d_created)\n" \
            "VALUES({id_prod},{id_com},{product_price},{current_time_str})")
            cursor.execute(sql,  (id_prod, id_com,product_price,current_time_str))
            conn.commit()
            #product_id = cursor.lastrowid # Get the ID of the newly inserted product
            #conn.commit()
            conversation_action.clear()
            del context.user_data['product_name']
            del context.user_data['product']
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            await update.message.reply_text(
                "An unexpected error occurred. Please try again later."
            )
        finally:
            if conn:
                conn.close()
    else:
        conversation_action.clear()
        logger.debug("Command not understood.")
        await update.message.reply_text(
            "🤔 Sorry, I don't understand that command.\n"\
            "Use `/hi` to see what I can do!\n" \
            "Business commands:\n"
            "List: /lb\n" \
            "Add new: /ab <Business Name> <Location>\n" \
            "Products:\n" \
            "List: /lp [pattern]\n"
        )

# --- Main Bot Setup ---
def main() -> None:
    """Runs the bot."""
    # Create the Application and pass your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers for different commands
    application.add_handler(CommandHandler("h", start_command))
    application.add_handler(CommandHandler("ap", add_product))
    application.add_handler(CommandHandler("lp", list_products))
    # De un determinado producto ver los precios
    application.add_handler(CommandHandler("lpp", list_product_price))
    application.add_handler(CommandHandler("mp", update_product))
    application.add_handler(CommandHandler("up", update_price))
    #select p.name, i.last_price, i.d_created, p.id_prod from 
    #products p LEFT JOIN prices i
    #ON i.id_prod = p.id_prod
    #where (p.id_prod, i.d_created) in(
    #select id_prod, max(d_created) from prices
    #group by id_prod

    application.add_handler(CommandHandler("lb", list_business))
    application.add_handler(CommandHandler("ab", add_business))
    application.add_handler(CallbackQueryHandler(set_agent_callback))

    # Register a handler for unknown commands (always put this last)
    #application.add_handler(MessageHandler(filters.COMMAND, handle_text_input))

    # Listen for any text message that is NOT a command
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))

    # Start the Bot
    logger.info("Bot started polling...")
    #application.run_polling(allowed_updates=Update.ALL_TYPES)
    application.run_polling()

if __name__ == '__main__':
    main()
