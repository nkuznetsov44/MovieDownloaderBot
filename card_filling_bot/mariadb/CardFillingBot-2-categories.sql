LOCK TABLES `category` WRITE;
/*!40000 ALTER TABLE `category` DISABLE KEYS */;
INSERT INTO `category` VALUES ('ENTERTAINMENT','развлечения','планетарий,тусовка хеллоуин,подъемник,напитки и пуф,тусовка',0.80),('FOOD','еда','еда,ав,лавка,продукты,дикси,кофе,вкусвил,вкусвилл,вв,сладкое,сладости,вино,магнолия,вода,яндекс лавка,пятерочка,добрынинский,перекресток,перекрёсток,азбука вкуса,ав,.*( |^)рынок.*,дошик,сыр,овощи',0.80),('GIFT','подарки','.*( |^)подарок.*,.*( |^)подарки.*,цветы',1.00),('HOME','для дома','.*( |^)икеа.*,.*( |^)икея.*,.*( |^)ikea.*,.*( |^)оби.*,клининг,клиннинг',0.80),('OTHER','другое','',1.00),('PUBLIC_SERVICE','ЖКУ','интернет,жку,свет',1.00),('RESTAURANT','рестораны','фобо,кафе,еда,kfc,яндекс еда,крошка картошка,ресторан,хлеб,шоколадница,макдак,даблби,торро гриль,бар,сладости и кофе,кола,паб,икея еда,суши,якитория,жан-жак,чаевые,кухня,шаурма,udc',0.80),('TAXI','такси','такси',0.80),('TRAVEL','путешествия','билеты,места в самолете',1.00);
/*!40000 ALTER TABLE `category` ENABLE KEYS */;
UNLOCK TABLES;