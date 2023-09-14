#Использовать v8runner
#Использовать cmdline
#Использовать irac

Перем СЕРВЕР;
Перем БАЗА;
Перем SQL_СЕРВЕР;
Перем SQL_ПОЛЬЗОВАТЕЛЬ;
Перем SQL_ПАРОЛЬ;
Перем ПЛАТФОРМА_ВЕРСИЯ;
Перем ПУТЬ_К_ФАЙЛУ_БАЗЫ;
Перем ЭТО_СЕРВЕРНАЯ_БАЗА;
Перем ЭТО_RAS;
Перем СОЗДАВАТЬ_ПУСТЫЕ;
Перем ТИП_СУБД;

Перем Лог;
Перем Конфигуратор;
Перем КОД_РАЗРЕШЕНИЯ;

Функция Инициализация()
    
    Лог = Логирование.ПолучитьЛог("createTeamplateBase");
    Лог.УстановитьУровень(УровниЛога.Информация);
    
    Парсер = Новый ПарсерАргументовКоманднойСтроки();
    Парсер.ДобавитьИменованныйПараметр("-platform");
    Парсер.ДобавитьИменованныйПараметр("-server");
    Парсер.ДобавитьИменованныйПараметр("-base");
    Парсер.ДобавитьИменованныйПараметр("-sqlserver");
    Парсер.ДобавитьИменованныйПараметр("-sqlpassw");
    Парсер.ДобавитьИменованныйПараметр("-sqluser");
    Парсер.ДобавитьИменованныйПараметр("-cfdt");
    Парсер.ДобавитьИменованныйПараметр("-isras");
    Парсер.ДобавитьИменованныйПараметр("-uccode");
    Парсер.ДобавитьИменованныйПараметр("-createempty");
    Парсер.ДобавитьИменованныйПараметр("-dbmstype");
    
    Параметры = Парсер.Разобрать(АргументыКоманднойСтроки);
    
    ПЛАТФОРМА_ВЕРСИЯ = Параметры["-platform"];
    СЕРВЕР = Параметры["-server"];
    БАЗА = НРег(Параметры["-base"]);
    SQL_СЕРВЕР = НРег(Параметры["-sqlserver"]);
    Если Не ЗначениеЗаполнено(SQL_СЕРВЕР) Тогда
        SQL_СЕРВЕР = "localhost";
    КонецЕсли;
    SQL_ПОЛЬЗОВАТЕЛЬ = Параметры["-sqluser"];
    Если Не ЗначениеЗаполнено(SQL_ПОЛЬЗОВАТЕЛЬ) Тогда
        SQL_ПОЛЬЗОВАТЕЛЬ = ""
        КонецЕсли;
    SQL_ПАРОЛЬ = Параметры["-sqlpassw"];
    Если Не ЗначениеЗаполнено(SQL_ПАРОЛЬ) Тогда
        SQL_ПАРОЛЬ = "";
    КонецЕсли;
    
    ПУТЬ_К_ФАЙЛУ_БАЗЫ = Параметры["-cfdt"];
    Если Не ЗначениеЗаполнено(ПУТЬ_К_ФАЙЛУ_БАЗЫ) Тогда
        ПУТЬ_К_ФАЙЛУ_БАЗЫ = "";
    КонецЕсли;
    
    ТИП_СУБД = Параметры["-dbmstype"];
    Если Не ЗначениеЗаполнено(ТИП_СУБД) Тогда
        ТИП_СУБД = "MSSQLServer";
    КонецЕсли;
    
    ЭТО_RAS = ЗначениеЗаполнено(Параметры["-isras"]);
    КОД_РАЗРЕШЕНИЯ = Параметры["-uccode"];
    
    СОЗДАВАТЬ_ПУСТЫЕ = Параметры["-createempty"];
    
    ЛОГ.Отладка("ПЛАТФОРМА_ВЕРСИЯ = " + ПЛАТФОРМА_ВЕРСИЯ);
    ЛОГ.Отладка("СЕРВЕР = " + СЕРВЕР);
    ЛОГ.Отладка("БАЗА = " + БАЗА);
    ЛОГ.Отладка("SQL_СЕРВЕР = " + SQL_СЕРВЕР);
    ЛОГ.Отладка("ПУТЬ_К_ФАЙЛУ_БАЗЫ = " + ПУТЬ_К_ФАЙЛУ_БАЗЫ);
    ЛОГ.Отладка("ЭТО_RAS = " + ЭТО_RAS);
    ЛОГ.Отладка("СОЗДАВАТЬ_ПУСТЫЕ = " + СОЗДАВАТЬ_ПУСТЫЕ);
    
    //ПЛАТФОРМА_ВЕРСИЯ = "8.3.12.1685";
    //СЕРВЕР           = "devadapter";
    //БАЗА             = "dev_rkudakov_adapter_adapter";
    //SQL_ПОЛЬЗОВАТЕЛЬ = "sa";
    //SQL_ПАРОЛЬ = "Dmd1234";
    //ЭТО_RAS = ИСТИНА;
    
    ЭТО_СЕРВЕРНАЯ_БАЗА = ЗначениеЗаполнено(СЕРВЕР);
    
    Если ЭТО_RAS Тогда
        Конфигуратор = Новый УправлениеКластером1С(ПЛАТФОРМА_ВЕРСИЯ, СЕРВЕР + ":1545");
    Иначе
        Конфигуратор = Новый УправлениеКонфигуратором();
        Если ЗначениеЗаполнено(ПЛАТФОРМА_ВЕРСИЯ) Тогда
            Конфигуратор.ИспользоватьВерсиюПлатформы(ПЛАТФОРМА_ВЕРСИЯ);
        КонецЕсли;
        Если ЗначениеЗаполнено(КОД_РАЗРЕШЕНИЯ) Тогда
            Конфигуратор.УстановитьКлючРазрешенияЗапуска(КОД_РАЗРЕШЕНИЯ);
        КонецЕсли;
    КонецЕсли;
    
КонецФункции

Функция СоздатьСервернуюБазу1С()
    
    ПараметрыБазы1С = Новый Структура;
    ПараметрыБазы1С.Вставить("Сервер1С", СЕРВЕР);
    ПараметрыБазы1С.Вставить("ИмяИБ", БАЗА);
    
    ПараметрыСУБД = Новый Структура();
    
    Если ТИП_СУБД = "MSSQLServer" Тогда
        ПараметрыСУБД.Вставить("ТипСУБД", "MSSQLServer");
    Иначе
        ПараметрыСУБД.Вставить("ТипСУБД", "PostgreSQL");
    КонецЕсли;
    
    
    ПараметрыСУБД.Вставить("СерверСУБД", SQL_СЕРВЕР);
    
    Если ЗначениеЗаполнено(SQL_ПОЛЬЗОВАТЕЛЬ) Тогда
        ПараметрыСУБД.Вставить("ПользовательСУБД", SQL_ПОЛЬЗОВАТЕЛЬ);
    КонецЕсли;
    
    Если ЗначениеЗаполнено(SQL_ПАРОЛЬ) Тогда
        ПараметрыСУБД.Вставить("ПарольСУБД", SQL_ПАРОЛЬ);
    КонецЕсли;
    
    ПараметрыСУБД.Вставить("ИмяБД", БАЗА);
    ПараметрыСУБД.Вставить("СоздаватьБД", СОЗДАВАТЬ_ПУСТЫЕ);
    
    АвторизацияВКластере = Новый Структура;
    АвторизацияВКластере.Вставить("Имя", "");
    АвторизацияВКластере.Вставить("Пароль", "");
    
    Конфигуратор.СоздатьСервернуюБазу(ПараметрыБазы1С, ПараметрыСУБД, АвторизацияВКластере, Ложь, ПУТЬ_К_ФАЙЛУ_БАЗЫ);
    
КонецФункции

Процедура СоздатьСервернуюБазуRAS()
    
    Кластеры = Конфигуратор.Кластеры();
    // Обходим список кластеров
    Для Каждого Кластер Из Кластеры.Список() Цикл
        ЛОГ.Информация("Cluster name = " + Кластер.Получить("Имя"));
        ИБКластера = Кластер.ИнформационныеБазы();
        
        ПараметрыИБ = Новый Структура;
        Если ТИП_СУБД = "MSSQLServer" Тогда
            ПараметрыИБ.Вставить("ТипСУБД", Перечисления.ТипыСУБД.MSSQLServer);
            ПараметрыИБ.Вставить("СмещениеДат", "2000");
        Иначе
            ПараметрыИБ.Вставить("ТипСУБД", Перечисления.ТипыСУБД.PostgreSQL);
        КонецЕсли;
        
        ПараметрыИБ.Вставить("АдресСервераСУБД", SQL_СЕРВЕР);
        ПараметрыИБ.Вставить("ИмяБазыСУБД", БАЗА);
        
        Если ЗначениеЗаполнено(SQL_ПОЛЬЗОВАТЕЛЬ) Тогда
            ПараметрыИБ.Вставить("ИмяПользователяБазыСУБД", SQL_ПОЛЬЗОВАТЕЛЬ);
        КонецЕсли;
        
        Если ЗначениеЗаполнено(SQL_ПАРОЛЬ) Тогда
            ПараметрыИБ.Вставить("ПарольПользователяБазыСУБД", SQL_ПАРОЛЬ);
        КонецЕсли;
        
        ПараметрыИБ.Вставить("БлокировкаРегламентныхЗаданийВключена", Перечисления.СостоянияВыключателя.Включено);
        ПараметрыИБ.Вставить("ВыдачаЛицензийСервером", Перечисления.ПраваДоступа.Разрешено);
        
        
        СоздатьБазуСУБД = СОЗДАВАТЬ_ПУСТЫЕ;
        ИБКластера.Добавить(БАЗА, , СоздатьБазуСУБД, ПараметрыИБ);
    КонецЦикла;
    
КонецПроцедуры

Процедура СоздатьФайловуюБазу1С()
    Конфигуратор.СоздатьФайловуюБазу(БАЗА, ПУТЬ_К_ФАЙЛУ_БАЗЫ);
КонецПроцедуры

Процедура СоздатьФайловуюБазуRAS()
    ВызватьИсключение "Not implemented"
КонецПроцедуры

Инициализация();
Если ЭТО_СЕРВЕРНАЯ_БАЗА Тогда
    Если ЭТО_RAS Тогда
        Лог.Информация("Creating server base with RAS...");
        СоздатьСервернуюБазуRAS();
    Иначе
        Лог.Информация("Creating server base with 1C...");
        СоздатьСервернуюБазу1С();
    КонецЕсли;
Иначе
    Если ЭТО_RAS Тогда
        Лог.Информация("Creating file base with RAS...");
        СоздатьФайловуюБазуRAS();
    Иначе
        Лог.Информация("Creating file base with 1C...");
        СоздатьФайловуюБазу1С();
    КонецЕсли;
КонецЕсли;
Лог.Информация("script completed");