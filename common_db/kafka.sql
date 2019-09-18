-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: db
-- Generation Time: May 25, 2019 at 03:03 PM
-- Server version: 5.7.26
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
-- Database: `kafka`
--
CREATE DATABASE IF NOT EXISTS `kafka` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `kafka`;

-- --------------------------------------------------------

--
-- Table structure for table `message_flow`
--

CREATE TABLE `message_flow` (
  `id` int(11) NOT NULL,
  `listen_to_topic` varchar(50) DEFAULT NULL,
  `send_to_topic` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `message_flow`
--

INSERT INTO `message_flow` (`id`, `listen_to_topic`, `send_to_topic`) VALUES
(1, 'digital_signature', 'detection'),
(2, 'detection', 'extract'),
(3, 'clustering', 'extract'),
(4, 'extract', 'table_extract'),
(5, 'table_extract', 'business_rules'),
(6, 'business_rules', 'sap');


DROP TABLE IF EXISTS `grouped_message_flow`;
CREATE TABLE `grouped_message_flow` (
  `id` int(11) NOT NULL,
  `listen_to_topic` varchar(100) DEFAULT NULL,
  `send_to_topic` varchar(100) DEFAULT NULL,
  `message_group` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `grouped_message_flow`
--

INSERT INTO `grouped_message_flow` (`id`, `listen_to_topic`, `send_to_topic`, `message_group`) VALUES
(4, 'save_changes', NULL, 'Hold'),
(5, 'save_changes', 'run_business_rule', 'Submit'),
(6, 'run_business_rule', 'merge_table', 'Submit'),
(7, 'merge_table', 'generate_json', 'Submit'),
(8, 'save_changes', 'update_queue', 'TL Review'),
(9, 'save_changes', 'sap_inward', 'SAP Inward'),
(10, 'save_changes', 'update_queue', 'Reject'),
(11, 'update_queue', 'run_business_rule', 'Reject'),
(12, 'run_business_rule', 'sap_portal_inward', 'Reject'),
(13, 'sap_portal_inward', 'merge_table', 'Reject'),
(14, 'merge_table', 'generate_json', 'Reject'),
(15, 'generate_json', 'send_email', 'Reject'),
(16, 'save_changes', 'run_business_rule', 'Approve'),
(17, 'run_business_rule', 'update_queue', 'Approve'),
(18, 'save_changes', 'update_queue', 'TL Submit'),
(19, 'update_queue', 'merge_table', 'TL Submit'),
(20, 'merge_table', 'generate_json', 'TL Submit'),
(21, 'save_changes', 'run_business_rule', 'Process'),
(22, 'run_business_rule', 'sap_ui', 'Process');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `message_flow`
--
ALTER TABLE `message_flow`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `message_flow`
--
ALTER TABLE `message_flow`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;
COMMIT;

--
-- Indexes for table `grouped_message_flow`
--
ALTER TABLE `grouped_message_flow`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `grouped_message_flow`
--
ALTER TABLE `grouped_message_flow`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=24;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
