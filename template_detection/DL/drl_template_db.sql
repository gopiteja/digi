-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Apr 17, 2019 at 01:43 PM
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
-- Database: `template_db`
--
CREATE DATABASE IF NOT EXISTS `drl_template_db` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `drl_template_db`;

-- --------------------------------------------------------

--
-- Table structure for table `field_dict`
--

CREATE TABLE `field_dict` (
  `id` int(11) NOT NULL,
  `field_type` text,
  `variation` text
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `field_dict`
--

INSERT INTO `field_dict` (`id`, `field_type`, `variation`) VALUES
(1, 'samokee', '[]'),
(2, 'Invoice Name', '[\"Invoice No\", \"Invoice #\"]'),
(3, 'GSTIN of Vendor', '[\"GSTIN:\", \"GST NO:\", \"GST/UIN No.:\", \"GSTIN -\", \"GSTIN Number .\", \"GSTIN No:\", \"Companys GSTIN :\", \"GSTIN Number.\", \"GSTIN. :\"]'),
(4, 'GSTIN of WNS supply site', '[\"GSTIN:\", \"GST NO:\", \"GST1N Number :\", \"GSTIN/ Unique\", \"Customer GSTIN:\", \"GSTIN Number :\"]'),
(5, 'Invoice Date', '[\"Invoice Date\", \"Date.\", \"bill date:\", \"Date\", \"Date :\", \"Invoice Date :\", \"Dated\", \"Order Date:\", \"nvoice Date\", \"nvoice Date:\", \"Date:\", \"BILL PERIOD\", \"DATE\", \"Invoice Date 3\", \"Doc. Date\", \"Date : 0\", \"date\"]'),
(6, 'Invoice Number', '[\"Invoice No\", \"Invoice No.\", \"bill no:\", \"Invoice No.:\", \"Invoice No :\", \"TAX INVOICE No.\", \"invoice no\", \"Invoice Number\", \"Bill No.\", \"lnv. No.\", \"VAT REG. TIN\", \"Inv. No.\", \"Invoice No. :\", \"Bill No. :\", \"invoice no 4\", \"Document No\", \"Invoice No. : 1\", \"ijnvoice No.:\", \"Document Number 1\", \"Delivery Address\", \"INVOICE No:\", \"Doc. No\", \"Order No:\", \"Order No: #\"]'),
(7, 'Location of Vendor', '[\"THE BEATLE\", \"TEA & COFFEE SUPPLIER\", \"Berggruen Car Rentals Private Limited\", \"Premises Address :\", \"Total Solutions in Office Suppliers: All kinds of Printing, Stationery & House Keeping\"]'),
(8, 'Location of WNS supply site', '[\"Company:\", \"Details of Receiver (Billed to)\", \"Address :\", \"TO:\", \"WNS GLOBAL SERVICES (P) LTD.\", \"Address:\"]'),
(9, 'Total Amount', '[\"Net Payable\", \"this months charges\", \"Grand Total :\", \"GRAND TOTAL\", \"Total\", \"Grand Total\", \"Item Taxable Amount -\", \"Sub-Total\", \"INVOICE VALUE\", \"Total Invoice Value\", \"INVOICE VALUE >\", \"Total net amount\", \"TOTAL\", \"Grand Total:\", \"a\", \"Total Amount:\", \"AMOUNT 105\"]'),
(10, 'HSN', '[\"HSN/SAC CODE:\"]'),
(11, 'PAN', '[\"Pan No:\", \"Customer Permanent Account Number -\", \"PAN No:\", \"PAN :\", \"PAN:\", \"PAN No.\", \"PAN\", \"Companys PAN\", \": AAECI2781H\", \"PAN No\", \"u2019ANNo. :\"]'),
(12, 'Vendor Name', '[\"For\", \"favour of\"]'),
(13, '', '[\"Customer GSTIN/Unique ID -\"]'),
(14, 'First Party GST', '[\"GSTIN\", \"Party GSTIN :\", \"GSTIN/UIN\", \"GST NO:\", \"GST\", \"GSTIN :\", \"GST - Reg. NO.\", \"VAT REG. TIN\", \"Party GSTIN\", \"}STIN Number :\", \"/ GSTIN Number : 2\", \"GST1N Number :\", \"GSTIN:\", \"GSTIN. :\", \"GST - Reg. No.\"]'),
(15, 'Third Party GST', '[\"GSTIN. :\", \"GSTIN/UIN\", \"GST\", \"GST Service Tax Regn. No\", \"GSTIN/UIN:\", \"GST No.\", \"GST No\", \"ilSTIN Number :\", \"GSTIN.:\", \"GSTIN Number . 2\", \"GST Service Tax Regn. No 2\", \"GSTINNumber.\", \"GST NO.\", \"GSTIN. : 2\", \"GSTIN :\"]'),
(16, 'Base Amount', '[\"Total\", \"Amount\", \"TAXABLE AMOUNT\", \"Sub-Total\", \"Total gross\", \"SALES TOTAL\", \"TAXABLE AMOUNT 1\", \"RATE\"]'),
(17, 'HSN/SAC', '[\"SAC Code\"]'),
(18, 'SRN', '[\"Account Number 3214-8707-6\"]');

-- --------------------------------------------------------

--
-- Table structure for table `trained_info`
--

CREATE TABLE `trained_info` (
  `id` int(11) NOT NULL,
  `template_name` varchar(255) DEFAULT NULL,
  `field_data` text,
  `header_ocr` text NOT NULL,
  `footer_ocr` text NOT NULL,
  `address_ocr` text NOT NULL,
  `count` int(11) NOT NULL DEFAULT '1',
  `sample_paths` longtext,
  `ab_train_status` int(11) NOT NULL DEFAULT '0',
  `created_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `field_dict`
--
ALTER TABLE `field_dict`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `trained_info`
--
ALTER TABLE `trained_info`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `field_dict`
--
ALTER TABLE `field_dict`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT for table `trained_info`
--
ALTER TABLE `trained_info`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
