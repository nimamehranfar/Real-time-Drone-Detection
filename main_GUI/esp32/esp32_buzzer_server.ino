/*
 ESP32 Drone Alert - uses U8g2 for OLED
 mDNS: http://drone-alert.local:5000
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include <U8g2lib.h>

// wifi
const char* ssid = "iPhone";
const char* password = "Ahmad123";
const char* ap_ssid = "Drone-Setup";

// pins
const int BUZZER_PIN = 18;
const int BUTTON_PIN = 15;
const int LED_PIN = 2;

// oled - exact same pattern as your working code
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

WebServer server(5000);

// state
bool buzzerActive = false;
bool droneDetected = false;
bool warningActive = false;
String lastMessage = "";
String lastAlertType = "";
unsigned long lastBeepTime = 0;
unsigned long lastDisplayUpdate = 0;
unsigned long alertStartTime = 0;
const unsigned long BEEP_INTERVAL = 500;
const unsigned long DISPLAY_TIMEOUT = 10000;

// button debounce
bool lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 50;

void drawCentered(const char* text, int yOffset) {
    u8g2.clearBuffer();
    int width = u8g2.getStrWidth(text);
    int x = (128 - width) / 2;
    int y = 32 + yOffset;
    u8g2.drawStr(x, y, text);
    u8g2.sendBuffer();
}

void setup() {
    Serial.begin(115200);
    Serial.println("\nESP32 Drone Alert");
    
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    
    // init display - same as your working code
    u8g2.begin();
    u8g2.setFont(u8g2_font_6x10_tf);
    
    showStartup();
    connectWiFi();
    
    // endpoints
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/buzzer/on", HTTP_POST, handleBuzzerOn);
    server.on("/buzzer/off", HTTP_POST, handleBuzzerOff);
    server.on("/alert/drone", HTTP_POST, handleDroneAlert);
    server.on("/alert/warning", HTTP_POST, handleWarningAlert);
    server.on("/alert/clear", HTTP_POST, handleClearAlert);
    server.on("/test", HTTP_POST, handleTest);
    
    server.enableCORS(true);
    server.begin();
    Serial.println("Server ready on port 5000");
    
    showReady();
}

void loop() {
    server.handleClient();
    handleButton();
    handleBuzzer();
    handleDisplayTimeout();
}

// wifi
void connectWiFi() {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawUTF8(0, 12, "Connecting to WiFi");
    u8g2.drawUTF8(0, 26, ssid);
    u8g2.sendBuffer();
    
    Serial.print("Connecting to ");
    Serial.println(ssid);
    
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nConnected!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
        
        if (MDNS.begin("drone-alert")) {
            Serial.println("mDNS: drone-alert.local");
        }
        
        digitalWrite(LED_PIN, HIGH);
        
        u8g2.clearBuffer();
        u8g2.drawUTF8(0, 12, "WiFi Connected!");
        u8g2.drawUTF8(0, 30, "IP:");
        u8g2.drawUTF8(20, 30, WiFi.localIP().toString().c_str());
        u8g2.drawUTF8(0, 48, "drone-alert.local");
        u8g2.sendBuffer();
        
        tone(BUZZER_PIN, 1000, 200);
        delay(300);
        tone(BUZZER_PIN, 1500, 200);
        
    } else {
        Serial.println("\nWiFi failed, starting AP");
        WiFi.softAP(ap_ssid);
        
        u8g2.clearBuffer();
        u8g2.drawUTF8(0, 12, "WiFi FAILED");
        u8g2.drawUTF8(0, 30, "Connect to AP:");
        u8g2.drawUTF8(0, 44, ap_ssid);
        u8g2.sendBuffer();
        
        tone(BUZZER_PIN, 500, 500);
    }
    
    delay(2000);
}

// display
void showStartup() {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB14_tr);
    u8g2.drawUTF8(20, 25, "DRONE");
    u8g2.drawUTF8(15, 50, "DETECT");
    u8g2.sendBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);
    delay(1500);
}

void showReady() {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawUTF8(0, 12, "READY");
    u8g2.drawUTF8(0, 28, "Waiting for");
    u8g2.drawUTF8(0, 40, "detections...");
    u8g2.drawUTF8(0, 56, WiFi.localIP().toString().c_str());
    u8g2.sendBuffer();
}

void showDroneAlert(String message) {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB14_tr);
    u8g2.drawUTF8(5, 20, "DRONE!");
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawUTF8(0, 36, "DETECTED");
    
    if (message.length() > 21) message = message.substring(0, 21);
    u8g2.drawUTF8(0, 50, message.c_str());
    u8g2.drawUTF8(0, 62, "Press BTN to dismiss");
    u8g2.sendBuffer();
}

void showWarningAlert(String message) {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB14_tr);
    u8g2.drawUTF8(10, 20, "WARNING");
    u8g2.setFont(u8g2_font_6x10_tf);
    
    if (message.length() > 21) {
        u8g2.drawUTF8(0, 40, message.substring(0, 21).c_str());
        u8g2.drawUTF8(0, 52, message.substring(21).c_str());
    } else {
        u8g2.drawUTF8(0, 40, message.c_str());
    }
    u8g2.sendBuffer();
}

void showDismissed() {
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB14_tr);
    u8g2.drawUTF8(5, 35, "DISMISSED");
    u8g2.sendBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);
    delay(1000);
    showReady();
}

// handlers
void handleStatus() {
    StaticJsonDocument<300> doc;
    doc["connected"] = true;
    doc["buzzer_active"] = buzzerActive;
    doc["drone_detected"] = droneDetected;
    doc["warning_active"] = warningActive;
    doc["ip"] = WiFi.localIP().toString();
    doc["last_alert"] = lastAlertType;
    doc["last_message"] = lastMessage;
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void handleBuzzerOn() {
    buzzerActive = true;
    droneDetected = true;
    lastAlertType = "drone";
    alertStartTime = millis();
    lastDisplayUpdate = millis();
    
    if (server.hasArg("plain")) {
        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, server.arg("plain"));
        if (!error && doc.containsKey("message")) {
            lastMessage = doc["message"].as<String>();
        }
    }
    
    showDroneAlert(lastMessage.length() > 0 ? lastMessage : "Drone detected!");
    digitalWrite(LED_PIN, HIGH);
    lastBeepTime = 0;
    
    Serial.println("DRONE ALERT");
    server.send(200, "application/json", "{\"success\":true,\"type\":\"drone\"}");
}

void handleBuzzerOff() {
    buzzerActive = false;
    droneDetected = false;
    warningActive = false;
    noTone(BUZZER_PIN);
    digitalWrite(BUZZER_PIN, LOW);
    
    Serial.println("Dismissed");
    showDismissed();
    
    server.send(200, "application/json", "{\"success\":true}");
}

void handleDroneAlert() {
    buzzerActive = true;
    droneDetected = true;
    warningActive = false;
    lastAlertType = "drone";
    alertStartTime = millis();
    lastDisplayUpdate = millis();
    
    if (server.hasArg("plain")) {
        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, server.arg("plain"));
        if (!error && doc.containsKey("message")) {
            lastMessage = doc["message"].as<String>();
        }
    }
    
    showDroneAlert(lastMessage.length() > 0 ? lastMessage : "Drone detected!");
    digitalWrite(LED_PIN, HIGH);
    
    // start buzzer immediately with tone
    tone(BUZZER_PIN, 2000);  // 2kHz tone
    lastBeepTime = millis();
    
    Serial.println("DRONE: " + lastMessage);
    server.send(200, "application/json", "{\"success\":true,\"type\":\"drone\"}");
}

void handleWarningAlert() {
    warningActive = true;
    droneDetected = false;
    buzzerActive = false;
    lastAlertType = "warning";
    alertStartTime = millis();
    lastDisplayUpdate = millis();
    
    noTone(BUZZER_PIN);
    digitalWrite(BUZZER_PIN, LOW);
    
    if (server.hasArg("plain")) {
        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, server.arg("plain"));
        if (!error && doc.containsKey("message")) {
            lastMessage = doc["message"].as<String>();
        }
    }
    
    showWarningAlert(lastMessage.length() > 0 ? lastMessage : "Warning!");
    
    Serial.println("WARNING: " + lastMessage);
    server.send(200, "application/json", "{\"success\":true,\"type\":\"warning\"}");
}

void handleClearAlert() {
    buzzerActive = false;
    droneDetected = false;
    warningActive = false;
    noTone(BUZZER_PIN);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    
    showReady();
    
    Serial.println("Cleared");
    server.send(200, "application/json", "{\"success\":true}");
}

void handleTest() {
    tone(BUZZER_PIN, 1500, 300);
    
    u8g2.clearBuffer();
    u8g2.setFont(u8g2_font_ncenB14_tr);
    u8g2.drawUTF8(35, 35, "TEST");
    u8g2.sendBuffer();
    u8g2.setFont(u8g2_font_6x10_tf);
    delay(500);
    showReady();
    
    server.send(200, "application/json", "{\"success\":true}");
}

// button
void handleButton() {
    bool reading = digitalRead(BUTTON_PIN);
    
    if (reading != lastButtonState) {
        lastDebounceTime = millis();
    }
    
    if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
        if (reading == LOW && buzzerActive) {
            Serial.println("Button pressed");
            buzzerActive = false;
            droneDetected = false;
            noTone(BUZZER_PIN);
            digitalWrite(BUZZER_PIN, LOW);
            showDismissed();
        }
    }
    
    lastButtonState = reading;
}

// buzzer + LED sync - LED flashes with buzzer
void handleBuzzer() {
    static bool buzzerOn = false;
    
    if (buzzerActive && droneDetected) {
        unsigned long now = millis();
        // toggle every 300ms for beep pattern
        if (now - lastBeepTime >= 300) {
            if (buzzerOn) {
                noTone(BUZZER_PIN);
                digitalWrite(LED_PIN, LOW);  // LED OFF with buzzer
                buzzerOn = false;
            } else {
                tone(BUZZER_PIN, 2000);  // 2kHz tone
                digitalWrite(LED_PIN, HIGH); // LED ON with buzzer
                buzzerOn = true;
            }
            lastBeepTime = now;
        }
    } else {
        if (buzzerOn) {
            noTone(BUZZER_PIN);
            digitalWrite(LED_PIN, LOW);  // LED OFF when not alerting
            buzzerOn = false;
        }
    }
}

// timeout
void handleDisplayTimeout() {
    if (warningActive && (millis() - lastDisplayUpdate > DISPLAY_TIMEOUT)) {
        warningActive = false;
        showReady();
    }
}
