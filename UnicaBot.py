#!/usr/bin/env python3
# Written by Lorenzo L. Concas on base of the echo bot made by telegram

import  logging

from    telegram        import ReplyKeyboardMarkup
from    telegram.ext    import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)
import  telegram.ext

# bot purpose libs
import  json
import  time
from    requests        import Session
import UnicaInterface

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

reply_keyboard                      = [['Inserisci credenziali'],
                                       ['Attiva/Disattiva autonotifica'],
                                       ['Mostra Tasse'],
                                       ['Mostra informazioni versione'],
                                       ['Guida', 'Esci']]

markup                              = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

TELEGRAM_API_TOKEN                  = 'INSERT_TOKEN_HERE'

#global messages
BOT_VERSION                         = 'Release Candidate 1.0'

MSG_AUTONOTIFY_LOGIN_REQUIRED       = 'Per utilizzare questa funzione devi prima fare il login inserendo le credenziali'
MSG_AUTONOTIFY_ACTIVATED_MESSAGE    = 'Servizio attivato, il controllo viene fatto ogni 7 (sette) giorni a partire dal questo momento'
MSG_AUTONOTIFY_DEACTIVATED_MESSAGE  = 'Servizio disattivato'
MSG_WELCOME                         = 'Ciao sono UniCaTaxBot, il bot che ti avvisa quando arrivano tasse da pagare se sei iscritto all\'università di cagliari. Sono ancora in prova, si gentile con me. Per iniziare devi inserire le credenziali tramite il menu'

MSG_GUIDE                           = ('Per potere utilizzare il bot è necessario fornirgli le credenziali di acceso del libretto online di UniCa\n' +
                                      'Per farlo, è sufficiente premere il tasto \"Inserisci Credenziali\" e seguire le istruzioni digitando prima nome utente poi password.\n' + 
                                      'Completata la procedura il bot verificherà che i dati siano corretti, in caso affermativo sarà possibile utilizzare le varie funzioni a disposizione\n'+
                                      'La funzione di autonotifica controlla ogni 7 (sette) giorni a partire dal momento dell\'attivazione la presenza di nuove tasse\n' +
                                      "Nota : le credenziali vengono cancellate dalla chat automaticamente")

MSG_CREDENTIAL_STEP_USRNAME          = 'Nome utente salvato, digita ora la password'
MSG_CREDENTIAL_STEP_CHECK            = 'Credenziali salvate\nControllo che siano valide, dammi qualche secondo...'
MSG_CREDENTIAL_VALID                 = 'Credenziali corrette!'
MSG_CREDENTIAL_INVALID               = 'Sembra che qualcosa non vada, sicuro di aver inserito i dati corretti? Riesegui la procedura'
MSG_CREDENTIAL_EMPTY                 = 'Prima devi inserire le credenziali'
MSG_UNKNOWN_COMMAND                  = 'Non so ancora come rispondere a questo'
MSG_UNKNOWN_ERROR                    = 'Si è verificato un errore sconosciuto, puoi incolpare @lconcas per questo'
MSG_CHECKING                         = 'Dammi qualche secondo che controllo...'
MSG_READING_CREDENTIAL               = 'Digita il tuo username (senza @studenti.unica.it)'
MSG_CREDENTIAL_CHOOSE_CAREER         = 'Sembra che tu abbia intrapreso più carriere, scegline una (mi riferirò sempre a quella che sceglierai)'
MSG_CAREER_INVALID                   = 'Carriera non valida, riprova'
MSG_CAREER_AUTOCHOOSEN               = 'Scelta non valida, verrà selezionata l\'ultima carriera intrapresa'
MSG_CAREER_INVITE_TO_CHOOSE_CAREER   = 'Scegli un numero fra quelli in elenco'

DATA_CREDENTIALMESSAGE               = 'credentialMSG'
DATA_USERCHOICE                      = 'choice'
DATA_STATUS_READINGUSERNAME          = 'readingUsername'
DATA_STATUS_READINGPASSWORD          = 'readingPsw'
DATA_STATUS_READING_CAREER           = 'readingCareer'
DATA_AUTONOTIFY_KEY                  = 'autonotify'
DATA_AUTONOTIFY_JOB                  = 'autonotify_job'

CHOICE_INSERT_CREDENTIAL             = 'inserisci credenziali'
CHOICE_SHOW_TAXES                    = 'mostra tasse'
CHOICE_EXIT                          = 'esci'
CHOICE_GUIDE                         = 'guida'
CHOICE_TOGGLE_AUTONOTIFICATION       = 'attiva/disattiva autonotifica'
CHOICE_VERSION_INFORMATION           = 'mostra informazioni versione'

CORE_INTERFACE                       = 'unicaInterface'

DAY_IN_SECONDS                       = 86400
AUTO_NOTIFY_INTERVAL                 = 7*DAY_IN_SECONDS


def start(update, context):
    #print("new connection")
    context.user_data[CORE_INTERFACE] = UnicaInterface.UnicaInterface()
    update.message.reply_text(MSG_WELCOME, reply_markup=markup)   
    return CHOOSING

def button_choice(update, context):
    payload = update.message.text.lower()
    if not CORE_INTERFACE in context.user_data:
        #il bot probabilmente è stato spento
        return CHOOSING
    interface = context.user_data[CORE_INTERFACE]

    if payload == CHOICE_INSERT_CREDENTIAL:
        #salviamo il messaggio dato dalla rispota all'utente (ecco perche' non update.message ma la reply)
        context.user_data[DATA_CREDENTIALMESSAGE] = update.message.reply_text(MSG_READING_CREDENTIAL)
        context.user_data[DATA_USERCHOICE] = DATA_STATUS_READINGUSERNAME       
    elif payload == CHOICE_SHOW_TAXES:
        interface = context.user_data[CORE_INTERFACE]
        islogged = interface.isLogged()
        if islogged:
            update.message.reply_text(MSG_CHECKING)
            taxes_json = interface.getPaymentsJSON()           
            taxes_human = interface.getTaxesUserReadable(taxes_json)
            update.message.reply_text(taxes_human)
        else:
            update.message.reply_text(MSG_CREDENTIAL_EMPTY)
        return CHOOSING
    elif payload == CHOICE_EXIT:
        done(update, context)
        return CHOOSING
    elif payload == CHOICE_GUIDE:
        update.message.reply_text(MSG_GUIDE)
        return CHOOSING
    elif payload == CHOICE_TOGGLE_AUTONOTIFICATION:
        islogged = interface.isLogged()
        if not islogged:
            update.message.reply_text(MSG_AUTONOTIFY_LOGIN_REQUIRED)
            return CHOOSING
        if DATA_AUTONOTIFY_KEY not in context.user_data.keys():
            autonotify_status = True
            context.user_data[DATA_AUTONOTIFY_KEY] = True
            update.message.reply_text(MSG_AUTONOTIFY_ACTIVATED_MESSAGE)
        else:
            autonotify_status = context.user_data[DATA_AUTONOTIFY_KEY]
            context.user_data[DATA_AUTONOTIFY_KEY] = not autonotify_status

        job_queue = context.job_queue

        if DATA_AUTONOTIFY_JOB in context.user_data.keys():
            job = context.user_data[DATA_AUTONOTIFY_KEY]
        else:
            job = job_queue.run_repeating(callback=autoCheck, interval=AUTO_NOTIFY_INTERVAL, context={'user_data': context.user_data, 'chat_data': context.chat_data, 'update': update}, name="autoCheckJob")
            context.user_data['DATA_AUTONOTIFY_JOB'] = job
        
        if autonotify_status:
            job_queue.start()
        else:
            job_queue.stop()

        return CHOOSING
    elif payload == CHOICE_VERSION_INFORMATION:
        update.message.reply_text("Versione bot : " + BOT_VERSION)
        return CHOOSING
    return TYPING_REPLY

def regular_choice(update, context):
    print(update.message.text)
    return CHOOSING


def received_data(update, context):
    user_data = context.user_data
    payload = update.message.text

    #controlliamo se stiamo aspettando dei dati
    #in caso negativo torniamo al menu
    if DATA_USERCHOICE not in user_data.keys():
        return CHOOSING

    #else resettiamo la scelta
    choice = user_data[DATA_USERCHOICE]
    del user_data[DATA_USERCHOICE]

    interface = context.user_data[CORE_INTERFACE]

    #leggiamo lo username che ci ha spedito l'utente
    if choice == DATA_STATUS_READINGUSERNAME:
        #salviamo lo username nell'interfaccia
        interface.setUsername(payload)
        #cancelliamo l'username dalla chat
        update.message.delete()
        #segnamo lo step il prossimo step
        user_data[DATA_USERCHOICE] = DATA_STATUS_READINGPASSWORD
        #rimuoviamo il messaggio che chiedeva l'username
        username_message = context.user_data[DATA_CREDENTIALMESSAGE]
        username_message.delete()
        #in seguito inviamo e salviamo il messaggio dove viene chiesta la password
        context.user_data[DATA_CREDENTIALMESSAGE] = update.message.reply_text(MSG_CREDENTIAL_STEP_USRNAME)
        return TYPING_REPLY  
    elif choice == DATA_STATUS_READINGPASSWORD:
        #stesso discorso ma per la password, valgono i commenti dello step precedente
        interface.setPassword(payload)
        update.message.delete()
        #rimuoviamo il messaggio che chiedeva la password
        username_message = context.user_data[DATA_CREDENTIALMESSAGE]
        username_message.delete()
        #notifichiamo l'utente del controllo delle credenziali
        update.message.reply_text(MSG_CREDENTIAL_STEP_CHECK)
        #controlliamo che i dati siano validi
        login_result = interface.login()
        if login_result == UnicaInterface.LOGIN_OK:
            update.message.reply_text(MSG_CREDENTIAL_VALID)
        elif login_result == UnicaInterface.LOGIN_OK_MULTIPLE_CAREER:
            update.message.reply_text(MSG_CREDENTIAL_CHOOSE_CAREER)
            careers = json.loads(interface.getCareers())
            message = ""
            counter = 1 
            for career in careers:
                message = message + ('('+ str(counter) + ') - ' +
                           'Matricola : ' + career['matricola'] +
                           '\nCorso : ' + career['corso_studio'] + 
                           '\nStato corso : ' + career['stato_corso'] +
                           "\n" 
                          )
                counter = counter + 1
            #print(message)
            user_data[DATA_USERCHOICE] = DATA_STATUS_READING_CAREER
            update.message.reply_text(message)
            update.message.reply_text(MSG_CAREER_INVITE_TO_CHOOSE_CAREER)
            return TYPING_REPLY
        else:
            update.message.reply_text(MSG_CREDENTIAL_INVALID)
        return CHOOSING
    elif choice == DATA_STATUS_READING_CAREER:
        try:
            choosen_career = int(payload)
        except :
            user_data[DATA_USERCHOICE] = DATA_STATUS_READING_CAREER
            update.message.reply_text(MSG_CAREER_INVALID)
            return TYPING_REPLY
        careers = json.loads(interface.getCareers())


        if choosen_career < 1 or choosen_career > len(careers):
            update.message.reply_text(MSG_CAREER_AUTOCHOOSEN)
            choosen_career = 0
        else:
            choosen_career = choosen_career - 1
        
        choice_result = interface.selectCareer(choosen_career)
        
        if choice_result == UnicaInterface.LOGIN_OK:
            update.message.reply_text("Carriera scelta correttamente")
        else:
            update.message.reply_text(MSG_UNKNOWN_ERROR)
        return CHOOSING
    else:
        update.message.reply_text(MSG_UNKNOWN_COMMAND)

    return CHOOSING



def autoCheck(context):
    user_data = context.job.context['user_data']
    update = context.job.context['update']
    chat_id = update['message']['chat']['id']
    interface = user_data[CORE_INTERFACE]
    if interface.isLogged():
        tax = interface.getNewtax()
        if tax != "{}":
            context.bot.send_message(chat_id=chat_id, text=tax)



def done(update, context):
    user_data = context.user_data
    if 'choice' in user_data:
        del user_data['choice']

    del user_data[CORE_INTERFACE]  
    
    user_data.clear()
    return ConversationHandler.END


def main():
    print("UnicaTaxBot is starting...")   
    updater = Updater(TELEGRAM_API_TOKEN, use_context=True)
    
    dp = updater.dispatcher
    
    #si occupano di gestire la conversazione
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSING:   [MessageHandler(
                            Filters.regex
                                ('^(Inserisci credenziali|'+
                                    'Mostra Tasse|'+
                                    'Mostra informazioni versione|'+
                                    'Attiva/Disattiva autonotifica|'+
                                    'Guida|'+
                                    'Test|'+
                                    'Esci)$'
                                ),
                                button_choice
                            )                      
                        ],

            TYPING_CHOICE:  [MessageHandler(Filters.text,
                                           button_choice)
                            ],

            TYPING_REPLY:   [MessageHandler(Filters.text,
                                          received_data),
                            ],
        },

        fallbacks=[MessageHandler(Filters.regex('^Esci$'), done)]
    )

    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    print("Bot is running...")
    updater.idle()


if __name__ == '__main__':
    main()