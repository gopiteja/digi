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
-- Database: `io_configuration`
--
CREATE DATABASE IF NOT EXISTS `drl_io_configuration` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `drl_io_configuration`;

-- --------------------------------------------------------

--
-- Table structure for table `input_configuration`
--

CREATE TABLE `input_configuration` (
  `id` int(11) NOT NULL,
  `type` varchar(50) NOT NULL,
  `access_1` varchar(200) NOT NULL,
  `access_2` varchar(200) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `input_configuration`
--

INSERT INTO `input_configuration` (`id`, `type`, `access_1`, `access_2`) VALUES
(1, 'Document', './input', '');

-- --------------------------------------------------------

--
-- Table structure for table `output_configuration`
--

CREATE TABLE `output_configuration` (
  `id` int(11) NOT NULL,
  `type` varchar(50) NOT NULL,
  `access_1` varchar(200) NOT NULL,
  `access_2` varchar(200) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `output_configuration`
--

INSERT INTO `output_configuration` (`id`, `type`, `access_1`, `access_2`) VALUES
(1, 'Document', './output', '');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `input_configuration`
--
ALTER TABLE `input_configuration`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `output_configuration`
--
ALTER TABLE `output_configuration`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `input_configuration`
--
ALTER TABLE `input_configuration`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `output_configuration`
--
ALTER TABLE `output_configuration`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
