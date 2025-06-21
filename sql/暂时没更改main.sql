/*
 Navicat Premium Data Transfer

 Source Server         : py310goofish
 Source Server Type    : SQLite
 Source Server Version : 3030001
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3030001
 File Encoding         : 65001

 Date: 17/06/2025 00:17:17
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for chat_bargain_counts
-- ----------------------------
DROP TABLE IF EXISTS "chat_bargain_counts";
CREATE TABLE "chat_bargain_counts" (
  "chat_id" TEXT,
  "count" INTEGER DEFAULT 0,
  "last_updated" DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("chat_id")
);

-- ----------------------------
-- Table structure for items
-- ----------------------------
DROP TABLE IF EXISTS "items";
CREATE TABLE "items" (
  "item_id" TEXT,
  "data" TEXT NOT NULL,
  "price" REAL,
  "description" TEXT,
  "last_updated" DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY ("item_id")
);

-- ----------------------------
-- Table structure for messages
-- ----------------------------
DROP TABLE IF EXISTS "messages";
CREATE TABLE "messages" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "user_id" TEXT NOT NULL,
  "item_id" TEXT NOT NULL,
  "role" TEXT NOT NULL,
  "content" TEXT NOT NULL,
  "timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP,
  "chat_id" TEXT
);

-- ----------------------------
-- Table structure for sqlite_sequence
-- ----------------------------
DROP TABLE IF EXISTS "sqlite_sequence";
CREATE TABLE "sqlite_sequence" (
  "name",
  "seq"
);

-- ----------------------------
-- Auto increment value for messages
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 1039 WHERE name = 'messages';

-- ----------------------------
-- Indexes structure for table messages
-- ----------------------------
CREATE INDEX "idx_chat_id"
ON "messages" (
  "chat_id" ASC
);
CREATE INDEX "idx_timestamp"
ON "messages" (
  "timestamp" ASC
);
CREATE INDEX "idx_user_item"
ON "messages" (
  "user_id" ASC,
  "item_id" ASC
);

PRAGMA foreign_keys = true;
