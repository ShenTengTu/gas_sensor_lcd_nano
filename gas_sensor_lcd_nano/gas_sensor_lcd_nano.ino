/*
  MQ-4 referance:
    - http://www.geekstips.com/mq4-sensor-natural-gas-methane-arduino/
    - https://jayconsystems.com/blog/understanding-a-gas-sensor
*/
#include <avr/wdt.h>
#include <SerialCommands.h> // https://github.com/ppedro74/Arduino-SerialCommands
#include <RTClib.h>         // https://github.com/adafruit/RTClib
#include <SdFat.h>          // https://github.com/adafruit/SdFat
#include <LiquidCrystal.h>

// Common
#define BAUD 115200
// SerialCommands
#define SERIAL_CMD_BUFFER_LEN 32
#define SERIAL_CMD_DELIMETER ";"
#define SERIAL_CMD_ARG_DELIMETER " "
#define SERIAL_CMD_RESPONSE F("__RESPONSE__")
#define SERIAL_CMD_SUCCESS F("_CMD_SUCCESS_")
#define SERIAL_CMD_FAIL F("_CMD_FAIL_")
#define SERIAL_CMD_FINISH F("_CMD_FINISH_")
// SD Card
#define SPI_CS 10
#define DATA_DIR "SENSOR" // limit 8 characters (8.3 filenmae)
#define RECORD_FILE_EXT ".CSV"
#define RECORD_PER_N 6
#define SD_ERR_MKDIR_FAILD F("__MKDIR_FAILD__")
#define SD_ERR_CHDIR_FAILD F("__CHDIR_FAILD__")
#define SD_ERR_FILE_OPEN_FAILD F("_FILE_OPEN_FAILD_")
#define SD_ERR_SYNC_WRITE F("_ERR_SYNC_WRITE_")
// LCD
#define LCD_COLS 16
#define LCD_ROWS 2
#define LCD_RS 8
#define LCD_EN 9
#define LCD_D4 4
#define LCD_D5 5
#define LCD_D6 6
#define LCD_D7 7
// MQ-4
#define GAS_SENSOR_PIN A0
#define GAS_SENSOR_PREHEAT 20 // sec
#define SENSOR_RL 2.0         // 2k to 47k Ohms (higher more sensitive)
#define MQ4_RATIO 4.4         // MQ4 RS / R0 = 4.4 ppm
#define MQ4_R0 4.27           // from calibration program
// from curve fitting base on MQ-4 Characteristic plot
#define MQ4_LPG_a 13.988358
#define MQ4_LPG_b -0.321690
#define MQ4_CH4_a 11.140551
#define MQ4_CH4_b -0.350163
// Marco
#define SERIAL_PRINTLN(x) (Serial.println(F(x))) // for decrease RAM usage
#define STR_2_C_STR(x) (String(x).c_str())
#define STR_2_INT(x) (String(x).toInt())

// ********** //
static bool _is_proccessing_cmd_ = false;

typedef struct Record_t
{
  String timestamp;
  double LPG_ppm;
  double CH4_ppm;
  int sensor_value;
};

// Watchdog Reset
void software_reset(uint8_t prescaller)
{
  wdt_enable(prescaller);
  while (1){}
}

// ***** Components_t ***** //

/**
 * Used Components of the device
 */
typedef struct Components_t
{
  RTC_DS3231 rtc;
  SdFat sd_fat;
  SdFile sd_file;
  LiquidCrystal lcd = LiquidCrystal(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);
  bool have_sd_begun = false;
  bool have_preat = false;
  uint32_t unix_time_cache = 0;
  uint32_t counter = 0;
};

/*!
   \brief Initializes the components

   \param [IN] self    Pointer to the Components object
*/
void Components_init(struct Components_t *self)
{
  // LCD
  self->lcd.begin(LCD_COLS, LCD_ROWS);
  Components_lcd_update_line(self, 1, STR_2_C_STR(F("Init ...")));

  // RTC
  if (!self->rtc.begin())
  {
    SERIAL_PRINTLN("No RTC");
    Components_lcd_update_line(self, 0, "No RTC");
    software_reset(WDTO_1S);
  }

  if (self->rtc.lostPower())
  {
    SERIAL_PRINTLN("RTC lost power");
    Components_lcd_update_line(self, 0, "RTC lost power");
    self->rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); // compiler's time
  }

  self->unix_time_cache = Components_rtc_now(self).unixtime();

  // SD
  delay(1000); // needed delay for SD card creating directory correctly
  self->have_sd_begun = self->sd_fat.begin(SPI_CS);
  if (!self->have_sd_begun)
  {
    SERIAL_PRINTLN("No SD");
    Components_lcd_update_line(self, 0, "No SD");
  }
  else
  {
    Components_sd_mkdir(self, DATA_DIR);
    Components_sd_chdir(self, DATA_DIR);
  }
}

/*!
   \brief get current time from RTC .

   \param [IN] self      Pointer to the Components object
*/
DateTime Components_rtc_now(Components_t *self)
{
  return self->rtc.now();
}

/*!
   \brief Set RTC time.

   \param [IN] self Pointer to the Components object
   \param [IN] timestamp timestamp
*/
void Components_rtc_set_time(Components_t *self, uint32_t timestamp)
{
  self->rtc.adjust(DateTime(timestamp));
}

/*!
   \brief Safely create a directory on the SD card.

   \param [IN] self     Pointer to the Components object
   \param [IN] dir_path directory path
*/
void Components_sd_mkdir(Components_t *self, const char *dir_path)
{
  if (!self->sd_fat.exists(dir_path))
  {
    if (!self->sd_fat.mkdir(dir_path))
    {
      Components_lcd_update_line(self, 1, STR_2_C_STR(SD_ERR_MKDIR_FAILD));
      delay(100);
      self->sd_fat.errorHalt(SD_ERR_MKDIR_FAILD);
    }
  }
}

/*!
   \brief Change directory on the SD card.

   \param [IN] self     Pointer to the Components object
   \param [IN] dir_path directory path
*/
void Components_sd_chdir(Components_t *self, const char *dir_path)
{
  if (!self->sd_fat.chdir(dir_path))
  {
    Components_lcd_update_line(self, 1, STR_2_C_STR(SD_ERR_CHDIR_FAILD));
    delay(100);
    self->sd_fat.errorHalt(SD_ERR_CHDIR_FAILD);
  }
}

/*!
   \brief Opens a file on the SD card.

   \param [IN] self      Pointer to the Components object
   \param [IN] file_path Directory path
   \param [IN] mode      The mode in which to open the file

   \return a File object referring to the opened file
*/
void Components_sd_open(Components_t *self, const char *file_path, uint8_t mode)
{
  if (!self->sd_file.open(file_path, mode))
  {
    Components_lcd_update_line(self, 1, STR_2_C_STR(SD_ERR_FILE_OPEN_FAILD));
    delay(100);
    self->sd_fat.errorHalt(SD_ERR_FILE_OPEN_FAILD);
  }
}

/*!
   \brief Update the line content of  LCD 

   \param [IN] self    Pointer to the Components object
   \param [IN] line_no Number of the line
   \param [IN] string  The characters to write
*/
void Components_lcd_update_line(struct Components_t *self, uint8_t line_no, const char *string)
{
  if (line_no < LCD_ROWS)
  {
    self->lcd.setCursor(0, line_no);
    String str = String(string);
    for (uint8_t i = 0; i < (LCD_COLS - str.length()); i++)
    {
      str += " ";
    }
    self->lcd.write(STR_2_C_STR(str));
  }
}

/*!
   \brief Clear LCD

   \param [IN] self    Pointer to the Components object
*/
void Components_lcd_clear(struct Components_t *self)
{
  self->lcd.clear();
}

static Components_t components;

// ********** //

char SERIAL_CMD_BUFFER[SERIAL_CMD_BUFFER_LEN];
SerialCommands SERIAL_CMDs(&Serial, SERIAL_CMD_BUFFER, sizeof(SERIAL_CMD_BUFFER), SERIAL_CMD_DELIMETER, SERIAL_CMD_ARG_DELIMETER);

void cmd_execute_faild(SerialCommands *sender, const char *info)
{
  sender->GetSerial()->println(info);
  sender->GetSerial()->println(SERIAL_CMD_FAIL);
  Components_lcd_update_line(&components, 1, STR_2_C_STR(SERIAL_CMD_FAIL));
  sender->GetSerial()->println(SERIAL_CMD_FINISH);
  software_reset(WDTO_1S);
}

void CMD_H_default(SerialCommands *sender, const char *cmd)
{
  cmd_execute_faild(sender, "Unrecognized command.");
}

/**
   __REQUEST__
*/
void CMD_H_request(SerialCommands *sender)
{
  sender->GetSerial()->println(SERIAL_CMD_RESPONSE);
}

/**
   SYNC_TIME <timestamp>;
*/
void CMD_H_sync_time(SerialCommands *sender)
{
  _is_proccessing_cmd_ = true;
  Components_lcd_clear(&components);
  Components_lcd_update_line(&components, 0, "SYNC_TIME");

  uint8_t max_arg_len = 1;
  const char *args[max_arg_len];
  uint8_t i;
  for (i = 0; i < max_arg_len; i++)
  {
    args[i] = sender->Next();
  }

  // [arg_0] timestamp
  if (args[0] == NULL)
  {
    return cmd_execute_faild(sender, "Serial Command requires 1 arguments.\r\n  SYNC_TIME <timestamp>;  ");
  }
  sender->GetSerial()->print(F("args[0]: "));
  sender->GetSerial()->println(args[0]);

  uint32_t timestamp = STR_2_INT(args[0]);
  if (timestamp == 0)
  {
    return cmd_execute_faild(sender, "Invalid timestamp value.");
  }

  DateTime dt = Components_rtc_now(&components);
  sender->GetSerial()->println(F("before sync: "));
  sender->GetSerial()->println(STR_2_C_STR(dt.unixtime()));
  Components_rtc_set_time(&components, timestamp);
  dt = Components_rtc_now(&components);
  sender->GetSerial()->println(F("synced: "));
  sender->GetSerial()->println(STR_2_C_STR(dt.unixtime()));
  sender->GetSerial()->println(SERIAL_CMD_SUCCESS);
  Components_lcd_update_line(&components, 1, STR_2_C_STR(SERIAL_CMD_SUCCESS));

  sender->GetSerial()->println(SERIAL_CMD_FINISH);
  software_reset(WDTO_1S);
}

SerialCommand serial_cmds[2] = {
    SerialCommand("__REQUEST__", CMD_H_request),
    SerialCommand("SYNC_TIME", CMD_H_sync_time)};

void setup_serial_commands()
{
  for (int i = 0; i < 2; i++)
  {
    SERIAL_CMDs.AddCommand(&serial_cmds[i]);
  }
  SERIAL_CMDs.SetDefaultHandler(&CMD_H_default);
}

// ********** //

void prepare_record_file()
{
  if (components.have_sd_begun)
  {
    char dt_buf[] = "YYYYMMDD"; // 8.3 format
    char str[16] = "";
    strcat(str, Components_rtc_now(&components).toString(dt_buf));
    strcat(str, RECORD_FILE_EXT);
    Components_sd_open(&components, str, FILE_WRITE);
  }
}

void write_record(Record_t record)
{
  if (components.have_sd_begun)
  {
    if (components.sd_file.fileSize() == 0)
    {
      components.sd_file.println("timestamp,LPG_ppm,CH4_ppm");
    }
    String str = "";
    str += record.timestamp;
    str += ",";
    str += record.LPG_ppm;
    str += ",";
    str += record.CH4_ppm;
    components.sd_file.println(str);
    if (!components.sd_file.sync() || components.sd_file.getWriteError())
    {
      Components_lcd_update_line(&components, 1, STR_2_C_STR(SD_ERR_SYNC_WRITE));
      delay(100);
      components.sd_fat.errorHalt(SD_ERR_SYNC_WRITE);
    }
    components.sd_file.close();
  }
}

void display_record(DateTime dt, Record_t record, int flag)
{
  char dt_buf[] = "YY MMDD hh:mm:ss";
  Components_lcd_update_line(&components, 0, dt.toString(dt_buf));
  String str;
  if (flag > 0)
  {
    str = "LPG ";
    str += record.LPG_ppm;
    Components_lcd_update_line(&components, 1, STR_2_C_STR(str));
  }
  else
  {
    str = "CH4 ";
    str += record.CH4_ppm;
    Components_lcd_update_line(&components, 1, STR_2_C_STR(str));
  }
}

double mq4_calc_ppm(double adc_value, double RL, double R0, double a, double b)
{
  double sensor_volt = adc_value * (5.0 / 1023.0);
  double RS_air = ((5.0 * RL) / sensor_volt) - RL;
  if (RS_air < 0)
    RS_air = 0;
  double ratio = RS_air / R0;
  if (ratio <= 0 || ratio > 100)
    ratio = 0.01;
  double ppm = a * pow(ratio, b);
  if (ppm < 0)
    ppm = 0.0;
  if (ppm > 10000)
    ppm = 9999.9;
  return ppm;
}

void setup()
{
  wdt_disable();
  Serial.begin(BAUD);
  Components_init(&components);
  Components_lcd_clear(&components);
  setup_serial_commands();
}

void loop()
{
  wdt_reset();

  // get Serial command from PC if available
  SERIAL_CMDs.ReadSerial();

  // if have serial command to process, not to execute main task
  if (_is_proccessing_cmd_)
    return;

  // Get current time from RTC
  DateTime dt = Components_rtc_now(&components);
  int interval = dt.unixtime() - components.unix_time_cache;

  // for gas sensor preheat
  if (!components.have_preat)
  {
    String str = "Preheating ";
    str += (GAS_SENSOR_PREHEAT - interval);
    Components_lcd_update_line(&components, 1, STR_2_C_STR(str));
    components.have_preat = (interval >= GAS_SENSOR_PREHEAT);
    return;
  }

  // Make a sensor record
  double adc_value = analogRead(GAS_SENSOR_PIN);
  Record_t record = {
      dt.timestamp(),
      mq4_calc_ppm(adc_value, SENSOR_RL, MQ4_R0, MQ4_LPG_a, MQ4_LPG_b),
      mq4_calc_ppm(adc_value, SENSOR_RL, MQ4_R0, MQ4_CH4_a, MQ4_CH4_b)};
  // refresh LCD per 1 second
  if (interval >= 1)
  {
    components.unix_time_cache = dt.unixtime();
    components.counter = (components.counter + 1 + RECORD_PER_N) % RECORD_PER_N;
    // update LCD content
    display_record(dt, record, components.counter % 2);
    // write record per N sencond (RECORD_PER_N)
    if (components.counter == 0)
    {
      prepare_record_file();
      write_record(record);
    }
  }
}
