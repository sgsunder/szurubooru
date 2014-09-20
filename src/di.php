<?php
$dataDirectory = __DIR__
	. DIRECTORY_SEPARATOR . '..'
	. DIRECTORY_SEPARATOR . 'data';

$publicDataDirectory = __DIR__
	. DIRECTORY_SEPARATOR . '..'
	. DIRECTORY_SEPARATOR . 'public_html'
	. DIRECTORY_SEPARATOR . 'data';

return [
	\Szurubooru\Config::class => DI\object()->constructor($dataDirectory, $publicDataDirectory),

	\Szurubooru\ControllerRepository::class => DI\object()->constructor(DI\link('controllers')),
	\Szurubooru\Upgrades\UpgradeRepository::class => DI\object()->constructor(DI\link('upgrades')),

	'upgrades' => DI\factory(function (DI\container $container) {
		return [
			$container->get(\Szurubooru\Upgrades\Upgrade01::class),
			$container->get(\Szurubooru\Upgrades\Upgrade02::class),
			$container->get(\Szurubooru\Upgrades\Upgrade03::class),
			$container->get(\Szurubooru\Upgrades\Upgrade04::class),
		];
	}),

	'controllers' => DI\factory(function (DI\container $container) {
		return [
			$container->get(\Szurubooru\Controllers\AuthController::class),
			$container->get(\Szurubooru\Controllers\UserController::class),
			$container->get(\Szurubooru\Controllers\UserAvatarController::class),
			$container->get(\Szurubooru\Controllers\PostController::class),
			$container->get(\Szurubooru\Controllers\PostContentController::class),
		];
	}),
];