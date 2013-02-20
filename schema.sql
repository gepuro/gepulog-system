drop table if exists article;
create table article (
  id integer primary key autoincrement,
  title string not null,
  date_time string not null,
  category string,
  contents string not null
);



