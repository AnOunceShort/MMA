<?php
// Allow cross-origin requests
header('Access-Control-Allow-Origin: *');
header('Content-Type: application/json');

// Get all CSV files in the current directory
$files = glob("*.csv");

// Return the list as JSON
echo json_encode($files);
?>
