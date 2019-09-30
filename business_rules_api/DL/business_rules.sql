-- phpMyAdmin SQL Dump
-- version 4.8.5
-- https://www.phpmyadmin.net/
--
-- Host: db
-- Generation Time: May 25, 2019 at 03:20 PM
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
-- Database: `business_rules`
--
CREATE DATABASE IF NOT EXISTS `business_rules` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `business_rules`;

-- --------------------------------------------------------

--
-- Table structure for table `sequence_data`
--

DROP TABLE IF EXISTS `sequence_data`;
CREATE TABLE `sequence_data` (
  `id` int(11) NOT NULL,
  `template_name` varchar(255) DEFAULT NULL,
  `ifelse` varchar(255) DEFAULT NULL,
  `func_name` varchar(255) DEFAULT NULL,
  `parameters` varchar(255) DEFAULT NULL,
  `operation` varchar(255) DEFAULT NULL,
  `nested` tinyint(1) DEFAULT NULL,
  `rule_name` varchar(255) NOT NULL,
  `group` varchar(255) NOT NULL,
  `type` varchar(255) NOT NULL,
  `rule_string` longtext NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `sequence_data`
--

INSERT INTO `sequence_data` (`id`, `template_name`, `ifelse`, `func_name`, `parameters`, `operation`, `nested`, `rule_name`, `group`, `type`, `rule_string`) VALUES
(4, 'All', '', 'Select', 'ocr.PO Number', '', 0, 'FIELD LENGTH == 10', 'One', '', '[(\'if\', [([(\'norm\', [\'CompareKeyLength\',\"ocr.PO Number,==,10\"])],[(\'norm\', [\'Assign\',\"validation.PO Number,1\"])]),([],[(\'norm\', [\'Assign\',\"validation.PO Number,0\"])])])]'),
(5, 'All', '', 'Select', 'ocr.Invoice Date', '', 0, 'FIELD FORMAT = Date', 'One', '', '[(\'if\',[([(\'norm\', [\'Format\',\"ocr.Invoice Date,Date\"])],[(\'norm\', [\'Assign\',\"validation.Invoice Date,1\"])]),([], [(\'norm\', [\'Assign\',\"validation.Invoice Date,0\"])])])]\r\n'),
(7, 'All', '', 'Select', 'ocr.Invoice Total', '', 0, 'Field not equal to zero', 'One', '', '[(\'if\',[([(\'norm\', [\'CompareKeyValue\',\"ocr.Invoice Total,!=,0\"])],     [(\'norm\', [\'Assign\',\"validation.Invoice Total NonZero,1\"])]),([],[(\'norm\', [\'Assign\',\"validation.Invoice Total NonZero,0\"]),(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Invoice Total Zero\"])])])]\r\n'),
(8, 'All', '', 'Select', 'ocr.Vendor GSTIN', '', 0, 'FIELD FORMAT = GST', 'One', '', '[(\'if\',[([(\'norm\', [\'Format\',\"ocr.Vendor GSTIN,GST\"])],[(\'norm\', [\'Assign\',\"validation.Vendor GSTIN,1\"])]),([],[(\'norm\', [\'Assign\',\"validation.Vendor GSTIN,0\"])])])]'),
(13, 'All', '', 'Select', 'ocr.Billed To (DRL Name)', '', 0, 'Verify DRL name from list of names', 'One', '', '[(\'if\', [([(\'norm\', [\'ContainsSubString\',\"ocr.Billed To (DRL Name),reddy\"])],[(\'norm\', [\'Assign\',\"validation.Billed To (DRL Name),1\"])]),([],[(\'norm\', [\'Assign\',\"validation.Billed To (DRL Name),0\"]),(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Invoice not raised in DRL name\"])])])]'),
(14, 'All', '', 'Select', 'ocr.Digital Signature', '', 0, 'Verify Digital Signature and Update hardcopy', 'One', '', '[(\'if\', [([(\'norm\', [\'CompareKeyValue\',\"validation.Digital Signature,==,1\"])],[(\'norm\', [\'Assign\',\"business_rule.Hardcopy Received,NA\"])]),([],[(\'norm\',[\'Assign\',\"business_rule.Hardcopy Received,No\"])])])]'),
(15, 'All', '', 'Select', 'ocr.Document Heading', '', 0, 'Document Heading', 'Six', '', '[(\"if\",   [ ([(\'norm\', [\'ContainsSubString\',\"ocr.Document Heading,Quotation\"])],[(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Quotation\"])]), ([(\'norm\', [\'ContainsSubString\',\"ocr.Document Heading,Estimate\"])],[(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Estimate\"])]),([(\'norm\', [\'ContainsSubString\',\"ocr.Document Heading,Proforma\"])],[(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Proforma\"])]),([(\'norm\', [\'CompareKeyValue\',\"business_rule.Rejection Reason,==,Delivery Challan])],[(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Delivery Challan\"])]),([(\'norm\', [\'ContainsSubString\',\"ocr.Document Heading,Duplicate\"])],[(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Duplicate\"])])])]'),
(16, 'All', '', 'Select', '', '', 0, 'POPULATE PO', 'One', '', '[(\'norm\', [\'Assign\',\"business_rule.Invoice Type,PO\"])]'),
(17, 'All', '', 'Select', '', '', 0, 'POPULATE P2P', 'One', '', '[(\'norm\', [\'Assign\',\"business_rule.Process Type,P2P\"])]'),
(18, 'All', '', 'Select', 'ocr.case_id', '', 0, 'POPULATE PORTAL FOR FILENAME STARTING WITH 2', 'One', '', '[(\'if\', [([(\'norm\', [\'StartsWith\',\"ocr.case_id,2\"])],[(\'norm\', [\'Assign\',\"business_rule.Source Of Invoice,Portal\"]), (\'norm\', [\'Assign\',\"business_rule.Portal Reference Number,business_rule.case_id\"])]), ([],[(\'norm\', [\'Assign\',\"business_rule.Source Of Invoice,\"])])])]'),
(19, 'All', '', 'Select', 'ocr.Vendor Name,sap.Vendor Name', '', 0, 'Match SAP vs OCR', 'Four', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"ocr.Vendor Name,==,sap.Vendor Name\"])],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Vendor Name,1\"])]),\r\n                                               \r\n                                           ([],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Vendor Name,0\"])])\r\n                        \r\n                                          ])\r\n                                   \r\n                                   \r\n                                   ]'),
(20, 'All', '', 'Select', 'ocr.Vendor GSTIN, ocr.DRL GSTIN', '', 0, 'Populate Tax Code- 70 for CGST/SGST, 72 for IGST', 'Two', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValueRange\',\"ocr.Vendor GSTIN,==,ocr.DRL GSTIN,2\"])],[(\'norm\', [\'Assign\',\"business_rule.Tax Code,70\"])]),([],[(\'norm\', [\'Assign\',\"business_rule.Tax Code,72\"])])])]'),
(22, 'All', '', 'AssignWithCondition', '', '', 0, 'Populate Current Fiscal Year', 'One', '', '[(\'norm\',[\'FiscalYear\',\"business_rule.Fiscal Year\"])]'),
(23, 'All', '', 'AssignWithCondition', 'ocr.DRL GSTIN', '', 0, 'Populate Business Place based on DRL GSTIN', 'Three', '', '[(\'norm\', [\'Select\',\"business_rule.Business Place,drl_business.Business Place,drl_business.DRL GSTIN,ocr.DRL GSTIN\"])]'),
(24, 'All', '', 'assign', 'ocr.Invoice Date', '', 0, 'Calculate Invoice Within Six Months', 'Four', '', '[(\'if\', [  ([(\'norm\', [\'DateRange\',\"ocr.Invoice Date,before,180\"])],\r\n[(\'norm\', [\'Assign\',\"business_rule.Invoice Old Date Error,Invoice is within SIX Months\"])]),([], [(\'norm\', [\'Assign\',\"business_rule.Invoice Old Date Error,Invoice is Older than SIX Months\"])])])]\r\n'),
(25, 'All', '', 'assign', 'ocr.DRL GSTIN', '', 0, 'Update Vendor, DRL place of supply based on GST', 'Three', '', '[(\'norm\', [\'Select\',\"business_rule.DRL Place Of Supply,drl_business.State Name,drl_business.DRL GSTIN,ocr.DRL GSTIN\"])]'),
(27, 'All', '', 'assign', '', '', 0, 'POPULATE PO INVOICES', 'One', '', '[(\'norm\', [\'Assign\',\"business_rule.Work Type,PO Invoices\"])]'),
(28, 'All', '', 'assign', 'ocr.PO Number', '', 0, 'Populate Service invoice if PO number starts with- 30,41, 44,53,56,59,91,535\r\nPopulate Supply Invoice if PO Number starts with- 40,43,46,47,48,52,57,58,70,588', 'Four', '', '[(\'if\', [([(\'norm\', [\'StartsWith\',\"ocr.PO Number,30\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,41\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,44\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,53\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,56\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,59\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,91\"]), \'OR\',(\'norm\', [\'StartsWith\',\"ocr.PO Number,535\"])],\r\n                                            [(\'norm\', [\'Assign\',\"business_rule.Document Type,Service Invoice\"])]),    \r\n                                         ([(\'norm\', [\'StartsWith\',\"ocr.PO Number,40\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,43\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,46\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,47\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,48\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,52\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,57\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,58\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,70\"]), \'OR\', (\'norm\', [\'StartsWith\',\"ocr.PO Number,588\"])],\r\n                                            [(\'norm\', [\'Assign\',\"business_rule.Document Type,Supply Invoice\"])])\r\n                                        ])                               ]'),
(29, 'All', '', 'assign', 'ocr.Invoice Total', '', 0, 'Invoice Amount > 5 lakhs', 'Five', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"ocr.Invoice Total,>,500000\"])], [(\'norm\', [\'Assign\',\"validation.Invoice Total Five Lakhs,1\"])]), ([],[(\'norm\', [\'Assign\',\"validation.Invoice Total Five Lakhs,0\"])])])]'),
(30, 'All', '', 'assign', 'ocr.DRL GSTIN', '', 0, 'Check If DRLGSTIN IS VALID', 'Two', '', '[(\'if\', [  ([(\'norm\', [\'Contains\',\"drl_business.DRL GSTIN,ocr.DRL GSTIN\"])],[]),([],[(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Incorrect GSTIN of DRL\"])])])]'),
(31, 'All', '', 'assign', 'ocr.Vendor Name,business_rule.Document Type,ocr.DRL GSTIN,sap.Currency', '', 0, 'UPDATE BOT QUEUE BASED ON EXCLUSION LIST', 'Four', '', '[(\'if\', [  ([(\'norm\', [\'Contains\',\"solvent_list.Solvent,process_queue.ocr_text\"]), \'OR\',(\'norm\', [\'Contains\',\"vendor_list.Vendor,ocr.Vendor Name\"]), \'OR\',(\'norm\', [\'CompareKeyValue\',\"business_rule.Document Type,==,Service Invoice\"]),\'OR\',(\'norm\', [\'ContainsSubString\',\"process_queue.ocr_text,Job Work\"]), \'OR\', (\'norm\', [\'ContainsSubString\',\"process_queue.ocr_text,JobWork\"]),\'OR\',(\'norm\', [\'CompareKeyValue\',\"ocr.DRL GSTIN,==,37AAACD7999Q2ZI\"]),\'OR\',(\'norm\', [\'CompareKeyValue\',\"sap.Currency,!=,INR\"])],[(\'norm\', [\'Assign\',\"business_rule.Bot Queue,No\"])]),([],[(\'norm\', [\'Assign\',\"business_rule.Bot Queue,Yes\"])])])]\r\n'),
(38, 'All', '', 'Select', 'ocr.PO Number,sap.PO Number', '', 0, 'Match SAP vs OCR', 'Three', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"ocr.PO Number,==,sap.PO Number\"])], [(\'norm\', [\'Assign\',\"validation.PO Number,1\"])]),([],[(\'norm\', [\'Assign\',\"validation.PO Number,0\"])])])]\r\n'),
(39, 'All', '', 'Select', 'ocr.DC Number,sap.DC Number', '', 0, 'Match SAP vs OCR', 'Four', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"ocr.DC Number,==,sap.DC Number\"])],\r\n                                              [(\'norm\', [\'Assign\',\"validation.DC Number,1\"])]),\r\n                                               \r\n                                           ([],\r\n                                              [(\'norm\', [\'Assign\',\"validation.DC Number,0\"])])\r\n                        \r\n                                          ])\r\n                                   \r\n                                   \r\n                                   ]'),
(40, 'All', '', 'Select', 'business_rule.Tax Code,sap.Tax Code', '', 0, 'Match SAP vs OCR', 'Four', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"business_rule.Tax Code,==,sap.Tax Code\"])],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Tax Code,1\"])]),\r\n                                               \r\n                                           ([],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Tax Code,0\"])])\r\n                        \r\n                                          ])\r\n                                   \r\n                                   \r\n                                   ]'),
(41, 'All', '', 'Select', 'ocr.Invoice Total,sap.Invoice Total', '', 0, 'Match SAP vs OCR', 'Four', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"ocr.Invoice Total,==,sap.Invoice Total\"])],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Invoice Total,1\"])]),\r\n                                               \r\n                                           ([],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Invoice Total,0\"])])\r\n                        \r\n                                          ])\r\n                                   \r\n                                   \r\n                                   ]'),
(42, 'All', '', 'Select', 'ocr.Invoice Date,sap.Invoice Date', '', 0, 'Match SAP vs OCR', 'Four', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"ocr.Invoice Date,==,sap.Invoice Date\"])],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Invoice Date,1\"])]),\r\n                                               \r\n                                           ([],\r\n                                              [(\'norm\', [\'Assign\',\"validation.Invoice Date,0\"])])\r\n                        \r\n                                          ])\r\n                                   \r\n                                   \r\n                                   ]'),
(43, 'All', '', 'Select', 'business_rule.Portal Reference Number', '', 0, 'FIELD LENGTH == 10', 'Two', '', '[(\'if\', [([(\'norm\', [\'CompareKeyLength\',\"business_rule.Portal Reference Number,==,10\"])], [(\'norm\', [\'Assign\',\"validation.Portal Reference Number,1\"])]), ([],[(\'norm\', [\'Assign\',\"validation.Portal Reference Number,0\"])])])]'),
(44, 'All', '', 'Select', 'ocr.DRL GSTIN', '', 0, 'FIELD FORMAT = GST', 'One', '', '[(\'if\', [([(\'norm\', [\'Format\',\"ocr.DRL GSTIN,GST\"])],[(\'norm\', [\'Assign\',\"validation.DRL GSTIN,1\"])]),([],[(\'norm\', [\'Assign\',\"validation.DRL GSTIN,0\"])])])]'),
(45, 'All', '', 'Select', 'sap.SAP Inward Status', '', 0, 'Invoice already Inwarded', 'Six', '', '[(\'if\', [  ([(\'norm\', [\'ContainsSubString\',\"sap.SAP Inward Status,Invoice is already Entered\"])],                                               [(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Invoice already Inwarded\"])]),                                           ])                                    ]'),
(46, 'All', '', 'assign', 'ocr.Vendor GSTIN', '', 0, 'Update Vendor, DRL place of supply based on GST', 'Two', '', '[(\'norm\', [\'doAssignRange\',\"business_rule.TIN Number,ocr.Vendor GSTIN,2\"])]'),
(47, 'All', '', 'assign', 'business_rule.TIN Number', '', 0, 'Update Vendor, DRL place of supply based on GST', 'Three', '', '[(\'norm\', [\'Select\',\"business_rule.Vendor Place Of Supply,drl_business.State Name,drl_business.TIN Number,business_rule.TIN Number\"])]'),
(50, 'All', '', 'Select', 'sap.PO Error Message', '', 0, 'Missing PO', 'Six', '', '[(\'if\', [  ([(\'norm\', [\'ContainsSubString\',\"sap.PO Error Message,PO number does not exists\"])],                                               [(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Missing PO\"])]),                                           ])                                    ]'),
(51, 'All', '', 'Select', 'sap.SAP Inward Status', '', 0, 'Invalid Vendor', 'Six', '', '[(\'if\', [  ([(\'norm\', [\'ContainsSubString\',\"sap.SAP Inward Status,Vendor Not Found\"])],                                               [(\'norm\', [\'Assign\',\"business_rule.Rejection Reason,Invalid Vendor\"])]),                                           ])                                    ]'),
(52, 'All', '', '', '', '', 0, 'Update queue to TL Verify if invoice total is greater than 5 lakhs, else move to Approved', 'Seven', '', '[(\'if\',  [([(\'norm\', [\'CompareKeyValue\',\"validation.Invoice Total Five Lakhs,==,1\"])],[(\'norm\', [\'UpdateQueue\',\'Quality Control\'])]), ([],[(\'norm\', [\'UpdateQueue\',\'Approved\'])])])]'),
(53, 'All', '', '', '', '', 0, 'Digital signature', 'One', '', '[(\'if\', [([(\'norm\', [\'CompareKeyValue\',\"validation.Digital Signature,==,1\"])],[(\'norm\', [\'Assign\',\"ocr.Digital Signature,Yes\"])]),([],[(\'norm\',[\'Assign\',\"ocr.Digital Signature,No\"])])])]'),
(54, 'All', '', 'Transform', '', '', 0, 'Add one to Fiscal Year', 'One', '', '[(\'norm\', [\'Transform\',\"business_rule.Fiscal Year,business_rule.Fiscal Year,+,1\"])]'),
(55, 'All', '', 'Select', 'ocr.DRL GSTIN', '', 0, 'Populate Tax Code- 00 for sez invoices', 'Three', '', '[(\'if\', [  ([(\'norm\', [\'CompareKeyValue\',\"ocr.DRL GSTIN,==,37AAACD7999Q2ZI\"])],[(\'norm\', [\'Assign\',\"business_rule.Tax Code,00\"])]),([],[])])]'),
(56, 'All', '', 'Select', 'business_rule.Tax Code', '', 0, 'Change SGST,CGST and IGST based on Tax code', 'Three', '', '[(\'if\', [([(\'norm\', [\'CompareKeyValue\',\"business_rule.Tax Code,==,70\"])],[(\'norm\', [\'Assign\',\"ocr.IGST Amount,0\"])]),([],[(\'norm\',[\'Assign\',\"ocr.SGST/CGST Amount,0\"])])])]'),
(57, 'All', '', 'Select', 'business_rule.Tax Code', '', 0, 'Change SGST,CGST and IGST based on Tax code', 'Three', '', '[(\'if\', [([(\'norm\', [\'CompareKeyValue\',\"business_rule.Tax Code,==,00\"])],[(\'norm\', [\'Assign\',\"ocr.IGST Amount,0\"])]),([],[])])]'),
(58, 'All', '', 'Select', 'business_rule.Tax Code', '', 0, 'Change SGST,CGST and IGST based on Tax code', 'Three', '', '[(\'if\', [([(\'norm\', [\'CompareKeyValue\',\"business_rule.Tax Code,==,00\"])],[(\'norm\', [\'Assign\',\"ocr.SGST/CGST Amount,0\"])]),([],[])])]\r\n');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `sequence_data`
--
ALTER TABLE `sequence_data`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `sequence_data`
--
ALTER TABLE `sequence_data`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=59;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
