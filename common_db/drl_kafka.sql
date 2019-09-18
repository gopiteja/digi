-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Apr 17, 2019 at 01:40 PM
-- Server version: 10.1.38-MariaDB
-- PHP Version: 7.3.3

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
CREATE DATABASE IF NOT EXISTS `drl_kafka` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `drl_kafka`;

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
(1, 'detection', 'extract'),
(2, 'clustering', 'extract'),
(3, 'extract', 'table_extract'),
(4, 'table_extract', NULL),
(5, 'business_rules', NULL);

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

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
