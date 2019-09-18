-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: db
-- Generation Time: May 08, 2019 at 09:52 AM
-- Server version: 5.7.25
-- PHP Version: 7.2.14

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `extraction`
--
CREATE DATABASE IF NOT EXISTS `extraction` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `extraction`;

-- --------------------------------------------------------

--
-- Table structure for table `business_rule`
--

DROP TABLE IF EXISTS `business_rule`;
CREATE TABLE `business_rule` (
  `id` int(11) NOT NULL,
  `case_id` varchar(255) NOT NULL,
  `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `Vendor Place Of Supply` varchar(255) DEFAULT NULL,
  `DRL Place Of Supply` varchar(255) DEFAULT NULL,
  `Business Place` varchar(255) DEFAULT NULL,
  `Invoice Type` varchar(255) DEFAULT NULL,
  `Process Type` varchar(255) DEFAULT NULL,
  `Work Type` varchar(255) DEFAULT NULL,
  `Source Of Invoice` varchar(255) DEFAULT NULL,
  `Verify Operator` varchar(255) DEFAULT NULL,
  `Portal Reference Number` varchar(255) DEFAULT NULL,
  `Invoice Old Date Error` varchar(255) DEFAULT NULL,
  `Fiscal Year` varchar(255) DEFAULT NULL,
  `Tax Code` varchar(255) DEFAULT NULL,
  `Batch ID` varchar(255) DEFAULT NULL,
  `Bot Queue` varchar(255) DEFAULT NULL,
  `Rejection Reason` varchar(255) DEFAULT NULL,
  `Rejection Status` varchar(255) DEFAULT NULL,
  `Hardcopy Received` varchar(255) DEFAULT NULL,
  `TIN Number` varchar(100) DEFAULT NULL,
  `Document Type` varchar(255) DEFAULT NULL,
  `Comments` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `combined`
--

DROP TABLE IF EXISTS `combined`;
CREATE TABLE `combined` (
  `id` int(11) NOT NULL,
  `case_id` text,
  `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `highlight` text,
  `Batch ID` text,
  `Billed To (DRL Name)` text,
  `Bot Processed` varchar(255) DEFAULT NULL,
  `Bot Queue` text,
  `Business Place` text,
  `Buyer Code` text,
  `Buyer Email ID` text,
  `Case Manager URL` text,
  `Case Manager Case Status` text,
  `Case Manager Message` text,
  `Case Manager Timestamp` text,
  `Comments` text,
  `Currency` text,
  `DC Number` text,
  `DRL GSTIN` text,
  `DRL Place Of Supply` text,
  `Digital Signature` text,
  `Document Heading` text,
  `Document Type` text,
  `FI Document Number` varchar(255) DEFAULT NULL,
  `Fiscal Year` text,
  `GRN Number` text,
  `Gross Amount` text NOT NULL,
  `GST Percentage` text,
  `HSN/SAC` text,
  `Hardcopy Received` text,
  `IGST Amount` text,
  `Invoice Base Amount` text,
  `Invoice Date` text,
  `Invoice Number` text,
  `Invoice Old Date Error` text,
  `Invoice Received Date` text,
  `Invoice Total` text,
  `Invoice Type` text,
  `Orchestrator Queue` varchar(255) DEFAULT NULL,
  `PO Error Message` text,
  `PO Number` text,
  `PO Type` text,
  `Payment Due Date` text,
  `Plant` text,
  `Portal Error Message` text,
  `Portal Reference Number` text,
  `Process Type` text,
  `Product description` text,
  `Quantity` text,
  `Rate` text,
  `Rejection Reason` text,
  `Rejection Status` text,
  `SAP Inward Number` text,
  `SAP Inward Status` text,
  `SGST/CGST Amount` text,
  `Service Entry Number` text,
  `Source Of Invoice` text,
  `Special Instructions` text,
  `TIN Number` text,
  `Tax Code` text,
  `Terms Of Payment` text,
  `Vendor Code` text,
  `Vendor Email ID` text,
  `Vendor GSTIN` text,
  `Vendor Name` text,
  `Vendor Place Of Supply` text,
  `Verify Operator` text,
  `Work Type` text,
  `Email Subject` text NOT NULL,
  `RPA Processed` varchar(255) NOT NULL,
  `RPA Error Message` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `drl_business`
--

DROP TABLE IF EXISTS `drl_business`;
CREATE TABLE `drl_business` (
  `id` bigint(20) NOT NULL,
  `State Name` text,
  `TIN Number` text,
  `Business Place` text,
  `DRL GSTIN` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `drl_business`
--

INSERT INTO `drl_business` (`id`, `State Name`, `TIN Number`, `Business Place`, `DRL GSTIN`) VALUES
(1, 'Andhra Pradesh – SEZ', '37', 'AP02', '37AAACD7999Q2ZI'),
(2, 'Assam', '18', 'AS01', '18AAACD7999Q1ZJ'),
(3, 'Bihar', '10', 'BR01', '10AAACD7999Q1ZZ'),
(4, 'Chandigarh', '04', 'CG01', '04AAACD7999Q1ZS'),
(5, 'Chattisgarh', '22', 'CH01', '22AAACD7999Q1ZU'),
(6, 'Daman', '25', 'DM01', '25AAACD7999Q1ZO'),
(7, 'Delhi', '07', 'DL01', '07AAACD7999Q1ZM'),
(8, 'Goa', '30', 'GA01', '30AAACD7999Q3ZV'),
(9, 'Gujarat', '24', 'GJ01', '24AAACD7999Q1ZQ'),
(10, 'Haryana', '06', 'HR01', '06AAACD7999Q1ZO'),
(11, 'Himachal Pradesh', '02', 'HP01', '02AAACD7999Q1ZW'),
(12, 'Jharkhand', '20', 'JH01', '20AAACD7999Q2ZX'),
(13, 'Karnataka', '29', 'KA01', '29AAACD7999Q1ZG'),
(14, 'Kerala', '32', 'KL01', '32AAACD7999Q1ZT'),
(15, 'Madhya Pradesh', '23', 'MP01', '23AAACD7999Q1ZS'),
(16, 'Maharashtra', '27', 'MH01', '27AAACD7999Q1ZK'),
(17, 'Orissa', '21', 'OR01', '21AAACD7999Q1ZW'),
(18, 'Puducherry', '34', 'PY01', '34AAACD7999Q1ZP'),
(19, 'Punjab', '03', 'PB01', '03AAACD7999Q1ZU'),
(20, 'Rajasthan', '08', 'RJ01', '08AAACD7999Q1ZK'),
(21, 'Tamil Nadu', '33', 'TN01', '33AAACD7999Q1ZR'),
(22, 'Telangana', '36', 'TS01', '36AAACD7999Q1ZL'),
(23, 'Uttar Pradesh', '09', 'UP01', '09AAACD7999Q1ZI'),
(24, 'Uttarakhand', '05', 'UK01', '05AAACD7999Q1ZQ'),
(25, 'West Bengal', '19', 'WB01', '19AAACD7999Q1ZH'),
(26, 'Andhra Pradesh', '37', 'AP01', '37AAACD7999Q1ZJ');

-- --------------------------------------------------------

--
-- Table structure for table `drl_names`
--

DROP TABLE IF EXISTS `drl_names`;
CREATE TABLE `drl_names` (
  `id` bigint(20) NOT NULL,
  `Names` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `drl_names`
--

INSERT INTO `drl_names` (`id`, `Names`) VALUES
(1, 'DR REDDY S LABORATORIES LTD'),
(2, 'Dr Reddy’s Laboratories Limited'),
(3, 'DR REDDY’S LABORATORIES LTD'),
(4, 'DR REDDYS LAB LTD'),
(5, 'DR REDDYS LABORATORIES LIMITED'),
(6, 'DR REDDYS LABORATORIES LTD.'),
(7, 'Reddys Laboratories Ltd.'),
(8, 'Reddys Laboratories Ltd'),
(9, 'Reddys Laboratories Limited'),
(10, 'M/s. Dr.Reddys (Biologies)'),
(11, 'M/s. Dr Reddys Laboratories'),
(12, 'M/s Dr.Reddys Laboratories Ltd.'),
(13, 'DRREDDYS LABORATORIES LTD'),
(14, 'Dr.Reddys Loboratories Limited IPDO'),
(15, 'Dr.Reddys Labotories Ltd,'),
(16, 'Dr.Reddys Laboratories-CTO'),
(17, 'Dr.Reddys Laboratories Ltd( Gland)'),
(18, 'Dr.Reddys Laboratories Ltd.,'),
(19, 'Dr.Reddys Laboratories Ltd.'),
(20, 'Dr.Reddys Laboratories Ltd,'),
(21, 'Dr.Reddys Laboratories Ltd-Central Warehouse'),
(22, 'Dr.Reddys Laboratories Ltd (CTO U-IV)'),
(23, 'Dr.Reddys Laboratories Ltd - (CPS Unit-I)'),
(24, 'Dr.Reddys Laboratories Ltd'),
(25, 'Dr.Reddys Laboratories Limited.'),
(26, 'DR.REDDYS LABORATORIES LIMITED RANGA REDDY'),
(27, 'DR.REDDYS LABORATORIES LIMITED'),
(28, 'Dr.Reddys Laboratories L.td'),
(29, 'Dr.Reddys Laboratories'),
(30, 'Dr.Reddys Lab.Ltd'),
(31, 'DR.REDDYS LAB'),
(32, 'Dr.Reddy’s Laboratories Ltd.'),
(33, 'Dr.Reddy’s Laboratories Ltd,'),
(34, 'Dr.Reddy’s Laboratories Ltd (Process Unit-2)'),
(35, 'Dr.Reddy’s Laboratories Ltd (Central Warehouse)'),
(36, 'Dr.Reddy’s Laboratories Ltd'),
(37, 'Dr.Reddy’s laboratories Ltd'),
(38, 'DR.REDDY’S LABORATORIES'),
(39, 'DR.REDDY S LAB.LTD.'),
(40, 'DR.REDDY LABS LTD,'),
(41, 'Dr. Reddys Pharmaceutical'),
(42, 'DR.REDDY LABS'),
(43, 'Dr. Reddys Labs Ltd'),
(44, 'Dr. Reddys Labs Limited'),
(45, 'Dr. Reddys Laboratory Ltd.'),
(46, 'Dr. Reddys Laboratories Ltd.Baddi'),
(47, 'Dr. Reddys Laboratory Ltd'),
(48, 'Dr. Reddys Laboratories Ltd.,'),
(49, 'Dr. REDDYS LABORATORIES LTD.'),
(50, 'Dr. Reddys Laboratories Ltd,'),
(51, 'Dr. Reddys Laboratories Ltd-Biologics Development Center'),
(52, 'Dr. Reddys Laboratories Limited.'),
(53, 'Dr. Reddys Laboratories Limited,'),
(54, 'Dr. Reddys Laboratories Limited FTO'),
(55, 'Dr. Reddys Laboratories Limited CTO-6'),
(56, 'Dr. Reddys Laboratories Limited CTO'),
(57, 'Dr. Reddys Laboratories Limited CPS -1'),
(58, 'Dr. Reddys Laboratories Limited CPS'),
(59, 'Dr. Reddys Laboratories Limited - IPDO'),
(60, 'DR. REDDYS LABORATORIES LIMITED'),
(61, 'DR. REDDYS LABORATORIES'),
(62, 'Dr. Reddys Laborateries Limited'),
(63, 'DR. REDDYS'),
(64, 'Dr Reddys Labs Ltd(CTO-2)'),
(65, '.Dr.Reddys Laboratories Ltd'),
(66, '.Dr. Reddys laboratories Ltd');

-- --------------------------------------------------------

--
-- Table structure for table `json_reader`
--

DROP TABLE IF EXISTS `json_reader`;
CREATE TABLE `json_reader` (
  `id` int(11) NOT NULL,
  `Portal Reference Number` varchar(200) NOT NULL,
  `Case Manager Message` varchar(200) DEFAULT NULL,
  `Case Manager Timestamp` varchar(200) DEFAULT NULL,
  `Case Manager Case Status` varchar(200) DEFAULT NULL,
  `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `json_reader`
--

INSERT INTO `json_reader` (`id`, `Portal Reference Number`, `Case Manager Message`, `Case Manager Timestamp`, `Case Manager Case Status`, `created_date`) VALUES
(0, '2000384624', 'Case already processed in CaseManager', '29/04/2019 04:09:15', 'Failure', '2019-04-29 10:39:22'),
(0, '2000384625', 'Case already processed in CaseManager', '29/04/2019 04:09:17', 'Failure', '2019-04-29 10:39:22'),
(0, '2000384626', 'Case already processed in CaseManager', '29/04/2019 04:09:18', 'Failure', '2019-04-29 10:39:22'),
(0, '2000384627', 'Successfully case created', '29/04/2019 04:09:18', 'Success', '2019-04-29 10:39:22'),
(0, '2000384628', 'Case already processed in CaseManager', '29/04/2019 04:09:18', 'Failure', '2019-04-29 10:39:22'),
(0, '2000384629', 'Case already processed in CaseManager', '29/04/2019 04:09:18', 'Failure', '2019-04-29 10:39:22'),
(0, '2000384630', 'Case already processed in CaseManager', '29/04/2019 04:09:18', 'Failure', '2019-04-29 10:39:22'),
(0, '2000384631', 'Successfully case created', '29/04/2019 04:09:19', 'Success', '2019-04-29 10:39:22'),
(0, '2000384632', 'Successfully case created', '29/04/2019 04:09:19', 'Success', '2019-04-29 10:39:27'),
(0, '2000384633', 'Successfully case created', '29/04/2019 04:09:20', 'Success', '2019-04-29 10:39:27'),
(0, '2000384634', 'Successfully case created', '29/04/2019 04:09:20', 'Success', '2019-04-29 10:39:28'),
(0, '2000384635', 'Successfully case created', '29/04/2019 04:09:20', 'Success', '2019-04-29 10:39:28'),
(0, '2000384638', 'Successfully case created', '29/04/2019 04:09:20', 'Success', '2019-04-29 10:39:28'),
(0, '2000384641', 'Successfully case created', '29/04/2019 04:09:21', 'Success', '2019-04-29 10:39:28'),
(0, '2000384642', 'Successfully case created', '29/04/2019 04:09:21', 'Success', '2019-04-29 10:39:28'),
(0, '2000384643', 'Successfully case created', '29/04/2019 04:09:21', 'Success', '2019-04-29 10:39:28'),
(0, '2000384644', 'Case already processed in CaseManager', '29/04/2019 04:09:21', 'Failure', '2019-04-29 10:39:28'),
(0, '2000384646', 'Case already processed in CaseManager', '29/04/2019 04:09:21', 'Failure', '2019-04-29 10:39:28'),
(0, '2000384647', 'Successfully case created', '29/04/2019 04:09:22', 'Success', '2019-04-29 10:39:28'),
(0, '2000384648', 'Successfully case created', '29/04/2019 04:09:22', 'Success', '2019-04-29 10:39:28'),
(0, '2000384649', 'Successfully case created', '29/04/2019 04:09:22', 'Success', '2019-04-29 10:39:28'),
(0, '2000384650', 'Successfully case created', '29/04/2019 04:09:23', 'Success', '2019-04-29 10:39:28'),
(0, '2000384651', 'Successfully case created', '29/04/2019 04:09:23', 'Success', '2019-04-29 10:39:28'),
(0, '2000384652', 'Case already processed in CaseManager', '29/04/2019 04:09:23', 'Failure', '2019-04-29 10:39:29'),
(0, '2000384653', 'Case already processed in CaseManager', '29/04/2019 05:38:58', 'Failure', '2019-04-29 12:08:59'),
(0, '2000384636', 'Successfully case created', '29/04/2019 05:36:06', 'Success', '2019-04-29 12:06:08'),
(0, '2000384637', 'Successfully case created', '29/04/2019 05:36:07', 'Success', '2019-04-29 12:06:13'),
(0, '2000384639', 'Successfully case created', '29/04/2019 05:36:08', 'Success', '2019-04-29 12:06:13'),
(0, '2000384640', 'Case already processed in CaseManager', '29/04/2019 05:38:55', 'Failure', '2019-04-29 12:08:59'),
(0, '2000384645', 'Case already processed in CaseManager', '29/04/2019 05:38:58', 'Failure', '2019-04-29 12:08:59'),
(0, '2000384654', 'Successfully case created', '29/04/2019 05:38:59', 'Success', '2019-04-29 12:08:59'),
(0, '2000384655', 'Case already processed in CaseManager', '29/04/2019 05:38:59', 'Failure', '2019-04-29 12:09:04'),
(0, '2000384656', 'Case already processed in CaseManager', '29/04/2019 05:38:59', 'Failure', '2019-04-29 12:09:04'),
(0, '2000384657', 'Case already processed in CaseManager', '29/04/2019 05:38:59', 'Failure', '2019-04-29 12:09:04'),
(0, '2000384658', 'Successfully case created', '29/04/2019 05:38:59', 'Success', '2019-04-29 12:09:04'),
(0, '2000384659', 'Case already processed in CaseManager', '29/04/2019 05:47:38', 'Failure', '2019-04-29 12:17:41'),
(0, '2000384660', 'Successfully case created', '29/04/2019 05:47:41', 'Success', '2019-04-29 12:17:41'),
(0, '2000384661', 'Successfully case created', '29/04/2019 05:47:41', 'Success', '2019-04-29 12:17:46'),
(0, '2000384662', 'Case already processed in CaseManager', '29/04/2019 05:47:41', 'Failure', '2019-04-29 12:17:46'),
(0, '2000384663', 'Case already processed in CaseManager', '29/04/2019 05:47:41', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384664', 'Successfully case created', '29/04/2019 05:47:42', 'Success', '2019-04-29 12:17:47'),
(0, '2000384665', 'Case already processed in CaseManager', '29/04/2019 05:47:42', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384666', 'Successfully case created', '29/04/2019 06:30:21', 'Success', '2019-04-29 13:00:22'),
(0, '2000384667', 'Case already processed in CaseManager', '29/04/2019 05:47:42', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384668', 'Case already processed in CaseManager', '29/04/2019 05:47:42', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384669', 'Successfully case created', '29/04/2019 05:47:43', 'Success', '2019-04-29 12:17:47'),
(0, '2000384670', 'Case already processed in CaseManager', '29/04/2019 05:47:43', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384671', 'Case already processed in CaseManager', '29/04/2019 05:47:43', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384672', 'Successfully case created', '29/04/2019 05:47:43', 'Success', '2019-04-29 12:17:47'),
(0, '2000384673', 'Case already processed in CaseManager', '29/04/2019 05:47:44', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384674', 'Case already processed in CaseManager', '29/04/2019 05:47:44', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384675', 'Case already processed in CaseManager', '29/04/2019 05:47:44', 'Failure', '2019-04-29 12:17:47'),
(0, '2000384676', 'Successfully case created', '29/04/2019 05:47:44', 'Success', '2019-04-29 12:17:47'),
(0, '2000384677', 'Successfully case created', '29/04/2019 05:47:45', 'Success', '2019-04-29 12:17:47'),
(0, '2000384678', 'Case already processed in CaseManager', '29/04/2019 05:47:45', 'Failure', '2019-04-29 12:17:48'),
(0, '2000384679', 'Case already processed in CaseManager', '29/04/2019 05:47:45', 'Failure', '2019-04-29 12:17:48'),
(0, '2000384683', 'Successfully case created', '29/04/2019 05:47:45', 'Success', '2019-04-29 12:17:48'),
(0, '2000384686', 'Successfully case created', '29/04/2019 05:47:46', 'Success', '2019-04-29 12:17:48'),
(0, '2000384687', 'Case already processed in CaseManager', '29/04/2019 05:47:46', 'Failure', '2019-04-29 12:17:48'),
(0, '2000384688', 'Successfully case created', '29/04/2019 05:47:46', 'Success', '2019-04-29 12:17:48'),
(0, '2000384689', 'Successfully case created', '29/04/2019 05:47:46', 'Success', '2019-04-29 12:17:48'),
(0, '2000384690', 'Successfully case created', '29/04/2019 06:30:22', 'Success', '2019-04-29 13:00:27'),
(0, '2000384692', 'Successfully case created', '29/04/2019 06:30:22', 'Success', '2019-04-29 13:00:27'),
(0, '2000384694', 'Successfully case created', '29/04/2019 06:30:23', 'Success', '2019-04-29 13:00:27'),
(0, '2000384696', 'Successfully case created', '29/04/2019 06:30:23', 'Success', '2019-04-29 13:00:27'),
(0, '2000384697', 'Successfully case created', '29/04/2019 06:30:23', 'Success', '2019-04-29 13:00:27'),
(0, '2000384699', 'Successfully case created', '29/04/2019 06:30:23', 'Success', '2019-04-29 13:00:27'),
(0, '2000384701', 'Successfully case created', '29/04/2019 06:30:24', 'Success', '2019-04-29 13:00:27'),
(0, '2000384702', 'Successfully case created', '29/04/2019 06:30:24', 'Success', '2019-04-29 13:00:27'),
(0, '2000384704', 'Successfully case created', '29/04/2019 06:30:25', 'Success', '2019-04-29 13:00:27'),
(0, '2000384402', 'Successfully case created', '30/04/2019 10:29:07', 'Success', '2019-04-30 16:59:14'),
(0, '2000384405', 'Successfully case created', '30/04/2019 10:29:08', 'Success', '2019-04-30 16:59:14'),
(0, '2000384406', 'Successfully case created', '30/04/2019 10:29:08', 'Success', '2019-04-30 16:59:14'),
(0, '2000384410', 'Successfully case created', '30/04/2019 10:29:09', 'Success', '2019-04-30 16:59:14'),
(0, '2000384411', 'Successfully case created', '30/04/2019 10:29:09', 'Success', '2019-04-30 16:59:15'),
(0, '2000384416', 'Successfully case created', '30/04/2019 10:29:09', 'Success', '2019-04-30 16:59:15'),
(0, '2000384417', 'Successfully case created', '30/04/2019 10:29:10', 'Success', '2019-04-30 16:59:15'),
(0, '2000384418', 'Successfully case created', '30/04/2019 10:29:10', 'Success', '2019-04-30 16:59:15'),
(0, '2000384419', 'Successfully case created', '30/04/2019 10:29:11', 'Success', '2019-04-30 16:59:15'),
(0, '2000384420', 'Successfully case created', '30/04/2019 10:29:11', 'Success', '2019-04-30 16:59:15'),
(0, '2000384421', 'Successfully case created', '30/04/2019 10:29:11', 'Success', '2019-04-30 16:59:15'),
(0, '2000384422', 'Successfully case created', '30/04/2019 10:29:11', 'Success', '2019-04-30 16:59:15'),
(0, '2000384423', 'Successfully case created', '30/04/2019 10:29:12', 'Success', '2019-04-30 16:59:15'),
(0, '2000384424', 'Successfully case created', '30/04/2019 10:29:12', 'Success', '2019-04-30 16:59:20'),
(0, '2000384425', 'Successfully case created', '30/04/2019 10:29:12', 'Success', '2019-04-30 16:59:20'),
(0, '2000384426', 'Successfully case created', '30/04/2019 10:29:13', 'Success', '2019-04-30 16:59:20'),
(0, '2000384427', 'Successfully case created', '30/04/2019 10:29:13', 'Success', '2019-04-30 16:59:20'),
(0, '2000384428', 'Successfully case created', '30/04/2019 10:29:13', 'Success', '2019-04-30 16:59:20'),
(0, '2000384896', 'Successfully case created', '06/05/2019 05:29:55', 'Success', '2019-05-06 12:00:21'),
(0, '2000384897', 'Successfully case created', '06/05/2019 05:29:57', 'Success', '2019-05-06 12:00:21'),
(0, '2000384898', 'Successfully case created', '06/05/2019 05:29:57', 'Success', '2019-05-06 12:00:26'),
(0, '2000384899', 'Successfully case created', '06/05/2019 05:29:58', 'Success', '2019-05-06 12:00:26'),
(0, '2000384900', 'Successfully case created', '06/05/2019 05:29:58', 'Success', '2019-05-06 12:00:26'),
(0, '2000384901', 'Successfully case created', '06/05/2019 05:29:59', 'Success', '2019-05-06 12:00:26'),
(0, '2000384902', 'Successfully case created', '06/05/2019 05:29:59', 'Success', '2019-05-06 12:00:27'),
(0, '2000384903', 'Successfully case created', '06/05/2019 05:30:00', 'Success', '2019-05-06 12:00:27'),
(0, '2000384905', 'Successfully case created', '06/05/2019 05:30:00', 'Success', '2019-05-06 12:00:27'),
(0, '2000384906', 'Successfully case created', '06/05/2019 05:30:00', 'Success', '2019-05-06 12:00:27'),
(0, '2000384907', 'Successfully case created', '06/05/2019 05:30:01', 'Success', '2019-05-06 12:00:27'),
(0, '2000384909', 'Successfully case created', '06/05/2019 05:30:01', 'Success', '2019-05-06 12:00:27'),
(0, '2000384910', 'Successfully case created', '06/05/2019 05:30:02', 'Success', '2019-05-06 12:00:27'),
(0, '2000384911', 'Successfully case created', '06/05/2019 05:30:02', 'Success', '2019-05-06 12:00:27'),
(0, '2000384912', 'Case already processed in CaseManager', '06/05/2019 05:39:06', 'Failure', '2019-05-06 12:09:09'),
(0, '2000384913', 'Successfully case created', '06/05/2019 05:39:10', 'Success', '2019-05-06 12:09:14'),
(0, '2000384277', 'Successfully case created', '07/05/2019 05:33:01', 'Success', '2019-05-07 12:03:05'),
(0, '2000384278', 'Successfully case created', '07/05/2019 05:33:02', 'Success', '2019-05-07 12:03:05'),
(0, '2000384279', 'Successfully case created', '07/05/2019 05:33:02', 'Success', '2019-05-07 12:03:06'),
(0, '2000384280', 'Successfully case created', '07/05/2019 05:33:03', 'Success', '2019-05-07 12:03:06'),
(0, '2000384281', 'Successfully case created', '07/05/2019 05:33:03', 'Success', '2019-05-07 12:03:06'),
(0, '2000384282', 'Successfully case created', '07/05/2019 05:33:04', 'Success', '2019-05-07 12:03:06'),
(0, '2000384283', 'Successfully case created', '07/05/2019 05:33:04', 'Success', '2019-05-07 12:03:11'),
(0, '2000384284', 'Successfully case created', '07/05/2019 05:33:04', 'Success', '2019-05-07 12:03:11'),
(0, '2000384285', 'Successfully case created', '07/05/2019 05:33:04', 'Success', '2019-05-07 12:03:11'),
(0, '2000384286', 'Successfully case created', '07/05/2019 05:33:05', 'Success', '2019-05-07 12:03:11'),
(0, '2000384288', 'Successfully case created', '07/05/2019 05:33:05', 'Success', '2019-05-07 12:03:11'),
(0, '2000384951', 'Successfully case created', '07/05/2019 05:33:06', 'Success', '2019-05-07 12:03:11');

-- --------------------------------------------------------

--
-- Table structure for table `ocr`
--

DROP TABLE IF EXISTS `ocr`;
CREATE TABLE `ocr` (
  `id` int(11) NOT NULL,
  `case_id` varchar(100) NOT NULL,
  `highlight` text,
  `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `PO Number` varchar(255) DEFAULT NULL,
  `Invoice Number` varchar(255) DEFAULT NULL,
  `Invoice Date` varchar(255) DEFAULT NULL,
  `Invoice Total` varchar(255) DEFAULT NULL,
  `Invoice Base Amount` varchar(255) DEFAULT NULL,
  `GST Percentage` varchar(255) DEFAULT NULL,
  `IGST Amount` varchar(255) DEFAULT NULL,
  `DRL GSTIN` varchar(255) DEFAULT NULL,
  `Vendor GSTIN` varchar(255) DEFAULT NULL,
  `Billed To (DRL Name)` varchar(255) DEFAULT NULL,
  `Vendor Name` varchar(255) DEFAULT NULL,
  `Special Instructions` varchar(255) DEFAULT NULL,
  `Digital Signature` varchar(255) DEFAULT NULL,
  `Document Heading` varchar(255) DEFAULT NULL,
  `HSN/SAC` varchar(255) DEFAULT NULL,
  `DC Number` varchar(255) DEFAULT NULL,
  `SGST/CGST Amount` varchar(255) DEFAULT NULL,
  `GRN Number` text,
  `Service Entry Number` text,
  `Comments` varchar(255) DEFAULT NULL,
  `Table` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `sap`
--

DROP TABLE IF EXISTS `sap`;
CREATE TABLE `sap` (
  `id` int(11) NOT NULL,
  `case_id` varchar(255) NOT NULL,
  `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `PO Number` varchar(255) DEFAULT NULL,
  `Invoice Number` varchar(255) DEFAULT NULL,
  `Invoice Date` varchar(255) DEFAULT NULL,
  `Invoice Total` varchar(255) DEFAULT NULL,
  `Currency` varchar(255) DEFAULT NULL,
  `Fiscal Year` varchar(255) DEFAULT NULL,
  `Vendor Code` varchar(255) DEFAULT NULL,
  `Buyer Email ID` varchar(255) DEFAULT NULL,
  `Buyer Code` varchar(255) DEFAULT NULL,
  `Plant` varchar(255) DEFAULT NULL,
  `PO Type` varchar(255) DEFAULT NULL,
  `SAP Inward Number` varchar(255) DEFAULT NULL,
  `Terms Of Payment` varchar(255) DEFAULT NULL,
  `Invoice Received Date` varchar(255) DEFAULT NULL,
  `Vendor Email ID` varchar(255) DEFAULT NULL,
  `DC Number` varchar(255) DEFAULT NULL,
  `SAP Inward Status` varchar(255) DEFAULT NULL,
  `Case Manager URL` varchar(255) DEFAULT NULL,
  `Service Entry Number` varchar(255) DEFAULT NULL,
  `GRN Number` varchar(255) DEFAULT NULL,
  `Vendor Name` varchar(255) DEFAULT NULL,
  `Tax Code` varchar(255) DEFAULT NULL,
  `Portal Error Message` varchar(255) DEFAULT NULL,
  `PO Error Message` varchar(255) DEFAULT NULL,
  `Payment Due Date` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `solvent_list`
--

DROP TABLE IF EXISTS `solvent_list`;
CREATE TABLE `solvent_list` (
  `id` bigint(20) NOT NULL,
  `Solvent` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `solvent_list`
--

INSERT INTO `solvent_list` (`id`, `Solvent`) VALUES
(1, 'Cyclo Hexanone'),
(2, 'Cyclohexane'),
(3, 'Dimethyl Formamide'),
(4, 'Methyl Tert-butyl Ether'),
(5, 'SBA'),
(6, 'Chloroform'),
(7, 'Ethyl Acetate'),
(8, 'Acetic Acid'),
(9, 'Acetone'),
(10, 'Hexane'),
(11, 'Iso Propyl Alcohol'),
(12, 'Methyl Iso Butyl Alcohol'),
(13, 'Methylene Chloride'),
(14, 'Toluene'),
(15, 'Orthoxylene'),
(16, 'Methanol'),
(17, 'Petroleum Ether'),
(18, 'Caustic Soda Lye'),
(19, 'Hydrochloric Acid'),
(20, 'Sulphuric Acid'),
(21, 'Ethyl Alcohol'),
(22, 'Acetonitrile');

-- --------------------------------------------------------

--
-- Table structure for table `validation`
--

DROP TABLE IF EXISTS `validation`;
CREATE TABLE `validation` (
  `id` int(11) NOT NULL,
  `case_id` varchar(100) NOT NULL,
  `highlight` varchar(255) DEFAULT NULL,
  `PO Number` varchar(255) DEFAULT NULL,
  `Invoice Number` varchar(255) DEFAULT NULL,
  `Invoice Date` varchar(255) DEFAULT NULL,
  `Invoice Total` varchar(255) DEFAULT NULL,
  `Invoice Total Five Lakhs` varchar(100) DEFAULT NULL,
  `Invoice Base amount` varchar(255) DEFAULT NULL,
  `GST Percentage` varchar(255) DEFAULT NULL,
  `IGST Amount` varchar(255) DEFAULT NULL,
  `DRL GSTIN` varchar(255) DEFAULT NULL,
  `Vendor GSTIN` varchar(255) DEFAULT NULL,
  `Billed To (DRL Name)` varchar(255) DEFAULT NULL,
  `Vendor Name` varchar(255) DEFAULT NULL,
  `Special instructions` varchar(255) DEFAULT NULL,
  `Digital Signature` varchar(255) DEFAULT NULL,
  `Document heading` varchar(255) DEFAULT NULL,
  `HSN/SAC` varchar(255) DEFAULT NULL,
  `DC Number` varchar(255) DEFAULT NULL,
  `SGST/CGST Amount` varchar(255) DEFAULT NULL,
  `Comments` varchar(255) DEFAULT NULL,
  `Invoice Total NonZero` varchar(100) DEFAULT NULL,
  `Portal Reference Number` varchar(255) DEFAULT NULL,
  `Tax Code` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `vendor_list`
--

DROP TABLE IF EXISTS `vendor_list`;
CREATE TABLE `vendor_list` (
  `id` bigint(20) NOT NULL,
  `Vendor` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `vendor_list`
--

INSERT INTO `vendor_list` (`id`, `Vendor`) VALUES
(1, 'Almelo Chemicals Pvt Ltd'),
(2, 'Anu\'s Laboratories Ltd'),
(3, 'A.R. Life Sciences Private Limited '),
(4, 'Gensynth Fine Chemicals Pvt. Ltd.'),
(5, 'Discovery Intermediates Pvt. Ltd.'),
(6, 'Dymes Pharmachem Limited'),
(7, 'Kekule Pharma Limited'),
(8, 'Kopalle Pharma Chemicals Pvt Ltd'),
(9, 'Shodhana Laboratories Ltd.'),
(10, 'Srini Pharmaceuticals Limited'),
(11, 'Synergene Active Ingredients Pvt Ltd'),
(12, 'Teckbond Laboratories Pvt Ltd'),
(13, 'Vegesna Laboratories Pvt. Ltd.'),
(14, 'Vijeta Life Sciences Pvt. Ltd.'),
(15, 'Vijayasri Group'),
(16, 'Vasant Chemicals Pvt Ltd'),
(17, 'Porus Laboratories Pvt Ltd'),
(18, 'Vindya Pharma India Pvt Ltd'),
(19, 'Frinze Laboratories Pvt. Ltd.'),
(20, 'Pravah Laboratories Pvt Ltd'),
(21, 'CTX Lifesciences Pvt. Ltd.'),
(22, 'Inter Labs (India) Private Limited'),
(23, 'Corvine Chemicals & Pharmaceuticals Limited'),
(24, 'Lantech Pharmaceuticals Ltd.'),
(25, 'Vineet Laboratories Pvt Ltd'),
(26, 'AE Logistics Pvt Ltd'),
(27, 'Agarwal Coal Corporation Pvt Ltd'),
(28, 'Agility Logistics Pvt Ltd'),
(29, 'Akin Logistics & Services Pvt Ltd.'),
(30, 'All Round Logistics'),
(31, 'Clinisafe Logistics'),
(32, 'Concord Maritime & Logistics'),
(33, 'DHL Express India Pvt Ltd'),
(34, 'Freight Systems (India) Pvt. Ltd.'),
(35, 'G.D.Bulk Carriers'),
(36, 'Gandhar Oil Refinery (India) Ltd'),
(37, 'Geetha Carriers'),
(38, 'Geo Fast Carriers Pvt. Ltd.'),
(39, 'Harika Shipping & Logistics'),
(40, 'Kiran Transport Company'),
(41, 'KMR Logistics'),
(42, 'Mahindra Logistics Limited'),
(43, 'Malwa Oil Carrier'),
(44, 'Mayuri Associates'),
(45, 'MK Logistics'),
(46, 'Mohd.Osman'),
(47, 'MOHIT MINERALS LIMITED'),
(48, 'Nanda Raoadlines'),
(49, 'Navin Transport'),
(50, 'Padmashri Road Lines'),
(51, 'Premier Bulk Carriers'),
(52, 'RL Logistics Private Limited'),
(53, 'S S Agencies'),
(54, 'Sai Baba Logistics'),
(55, 'Savani Carrying Pvt. Ltd.'),
(56, 'Shree Sai Divya Logistics Pvt Ltd'),
(57, 'Shree Sai Roadways'),
(58, 'SMS Carbon and Minerals Pvt Ltd'),
(59, 'Sreedhar Clearing Services Pvt. Ltd'),
(60, 'Sri Balaji Transport'),
(61, 'Sri Hanuman Carriers'),
(62, 'Sri Kalki Bhagavan Transport'),
(63, 'Sri Srinivasa Roadways'),
(64, 'Sri Tirumala Balaji Logistics'),
(65, 'SRI CHAKRA SUPPLY CHAIN S'),
(66, 'Sripak Logistics (P) Limited'),
(67, 'Stride Express Pvt Ltd'),
(68, 'The Singareni Collieries Co. Ltd.'),
(69, 'The Venkatramana enterprises'),
(70, 'Thirumalai Cold Transporters'),
(71, 'Triway Forwarders Pvt Ltd'),
(72, 'Waymark Logistics India Pvt Ltd.'),
(73, 'World Courier (I )Pvt Ltd'),
(74, 'World Courier (India) Pvt. Ltd.'),
(75, 'World Courier (India) Pvt. Ltd.'),
(76, 'Acacia Life Sciences Pvt Ltd');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `business_rule`
--
ALTER TABLE `business_rule`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `combined`
--
ALTER TABLE `combined`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `drl_business`
--
ALTER TABLE `drl_business`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_drl_business_index` (`id`);

--
-- Indexes for table `drl_names`
--
ALTER TABLE `drl_names`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_drl_excel_index` (`id`);

--
-- Indexes for table `ocr`
--
ALTER TABLE `ocr`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `sap`
--
ALTER TABLE `sap`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `solvent_list`
--
ALTER TABLE `solvent_list`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_solvent_list_index` (`id`);

--
-- Indexes for table `validation`
--
ALTER TABLE `validation`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `vendor_list`
--
ALTER TABLE `vendor_list`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_vendorlist_index` (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `business_rule`
--
ALTER TABLE `business_rule`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `combined`
--
ALTER TABLE `combined`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `drl_business`
--
ALTER TABLE `drl_business`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=27;

--
-- AUTO_INCREMENT for table `drl_names`
--
ALTER TABLE `drl_names`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=67;

--
-- AUTO_INCREMENT for table `ocr`
--
ALTER TABLE `ocr`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `sap`
--
ALTER TABLE `sap`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `solvent_list`
--
ALTER TABLE `solvent_list`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;

--
-- AUTO_INCREMENT for table `validation`
--
ALTER TABLE `validation`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `vendor_list`
--
ALTER TABLE `vendor_list`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=77;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
