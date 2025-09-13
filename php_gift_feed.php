<?php

declare(strict_types = 1);
error_reporting(E_ALL);

// LiveProto bootstrap (no composer needed)
if(file_exists('liveproto.php') === false){
	copy('https://installer.liveproto.dev/liveproto.php','liveproto.php');
	require_once 'liveproto.php';
} else {
	require_once 'liveproto.phar';
}

use Tak\Liveproto\Network\Client;
use Tak\Liveproto\Utils\Settings;
use Revolt\EventLoop;

// Ensure data directory exists
if(!is_dir('data')){
	@mkdir('data',0777,true);
}
$feedFile = __DIR__.DIRECTORY_SEPARATOR.'data'.DIRECTORY_SEPARATOR.'gifts_feed.jsonl';

// Settings (fill with your credentials)
$settings = new Settings();
$settings->setApiId(29784714); // <-- API ID
$settings->setApiHash('143dfc3c92049c32fbc553de2e5fb8e4'); // <-- API HASH
$settings->setDeviceModel('PC 64bit');
$settings->setSystemVersion('4.14.186');
$settings->setAppVersion('1.28.5');
$settings->setIPv6(false);
$settings->setHideLog(true);
$settings->setReceiveUpdates(false);

$client = new Client('gift_feed','sqlite',$settings);

function write_feed(string $file,array $gift,string $event = 'new') : void {
	$line = json_encode([
		'event' => $event,
		'gift'  => [
			'id' => $gift['id'] ?? 0,
			'title' => $gift['title'] ?? 'NONE',
			'stars' => $gift['stars'] ?? 0,
			'limited' => $gift['limited'] ?? true,
			'sold_out' => $gift['sold_out'] ?? false,
			'require_premium' => $gift['require_premium'] ?? false,
			'can_upgrade' => $gift['can_upgrade'] ?? false,
			'availability_remains' => $gift['availability_remains'] ?? null,
			'availability_total' => $gift['availability_total'] ?? null,
		]
	], JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
	if($line !== false){
		file_put_contents($file,$line.PHP_EOL,FILE_APPEND | LOCK_EX);
	}
}

EventLoop::unreference(EventLoop::repeat(2.00,function() use($client,$feedFile) : void {
	static $hash = 0;
	if($client->isAuthorized() and $client->connected){
		try {
			$starGifts = $client->payments->getStarGifts(hash : $hash);
			if($starGifts->getClass() === 'payments.starGifts'){
				if($hash === 0){
					$hash = $starGifts->hash;
				} else {
					$hash = $starGifts->hash;
					foreach($starGifts->gifts as $gift){
						if($gift->getClass() === 'starGift' and $gift->sold_out === false){
							$payload = [
								'id' => $gift->id,
								'title' => strval($gift->title ?: 'NONE'),
								'stars' => $gift->stars,
								'limited' => (bool)$gift->limited,
								'sold_out' => (bool)$gift->sold_out,
								'require_premium' => (bool)$gift->require_premium,
								'can_upgrade' => (bool)$gift->can_upgrade,
								'availability_remains' => $gift->availability_remains ?? null,
								'availability_total' => $gift->availability_total ?? null,
							];
							write_feed($feedFile,$payload,'new');
						}
					}
				}
			}
		} catch(Throwable $e){
			error_log(strval($e));
		}
	}
}));

$client->start();

?>


