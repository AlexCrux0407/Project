<?php
$file = $_FILES['image']['tmp_name'];
$api_key = 'TU_API_KEY';

$ocr_url = 'https://api.ocr.space/parse/image';

$post = [
    'apikey' => $api_key,
    'language' => 'eng',
    'isOverlayRequired' => false,
    'file' => new CURLFile($file)
];

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $ocr_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
$result = curl_exec($ch);
curl_close($ch);

echo $result;
?>
