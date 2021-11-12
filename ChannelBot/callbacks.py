import asyncio.exceptions
from Data import Data
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ButtonUrlInvalid
from ChannelBot.database.users_sql import remove_channel as urc
from ChannelBot.database.channel_sql import (
    remove_channel as crc,
    set_caption,
    set_buttons,
    set_sticker,
    set_position,
    set_edit_mode,
    toggle_webpage_preview,
    get_channel_info,
    get_sticker
)
from ChannelBot.manage import manage_channels
from ChannelBot.settings import channel_settings
from ChannelBot.string_to_buttons import string_to_buttons


# Callbacks
@Client.on_callback_query()
async def _callbacks(bot: Client, callback_query: CallbackQuery):
    user = await bot.get_me()
    user_id = callback_query.from_user.id
    mention = user["mention"]
    query = callback_query.data.lower()
    if query.startswith("home"):
        if query == 'home':
            chat_id = callback_query.from_user.id
            message_id = callback_query.message.message_id
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=Data.START.format(callback_query.from_user.mention, mention),
                reply_markup=InlineKeyboardMarkup(Data.buttons),
            )
        elif query == 'home+channels':
            success, buttons, text = await manage_channels(user_id, bot)
            if success:
                await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await callback_query.edit_message_text(text)
        elif query.startswith('home+'):
            channel_id = int(query.split("+")[-1])
            text, markup, sticker_id = await channel_settings(channel_id, bot)
            if text:
                await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
    elif query == "about":
        chat_id = callback_query.from_user.id
        message_id = callback_query.message.message_id
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=Data.ABOUT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(Data.home_buttons),
        )
    elif query == "help":
        chat_id = callback_query.from_user.id
        message_id = callback_query.message.message_id
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="**Veja como me usar**\n" + Data.HELP,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(Data.home_buttons),
        )
    elif query.startswith('settings'):
        channel_id = int(query.split('+')[1])
        text, markup, sticker_id = await channel_settings(channel_id, bot)
        if sticker_id:
            await callback_query.message.reply_sticker(sticker_id)
        if text:
            await callback_query.message.delete()
            await callback_query.message.reply(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
        else:
            await callback_query.answer('Canal não encontrado. Por favor, adicione novamente !', show_alert=True)
            await crc(channel_id)
            await urc(user_id, channel_id)
            await callback_query.message.delete()
    elif query.startswith('change'):
        change = query.split('+')[1]
        channel_id = int(query.split('+')[2])
        success, info = await get_channel_info(channel_id)
        if success:
            buttons = info['buttons']
            caption = info['caption']
            # position = info['position']
            # webpage_preview = info['webpage_preview']
            sticker_id = info['sticker_id']
            if change == 'caption':
                if caption:
                    buttons = [
                        [InlineKeyboardButton('Legenda de alteração', callback_data=f'add+{change}+{channel_id}')],
                        [InlineKeyboardButton('Remover legenda', callback_data=f'remove+{change}+{channel_id}')],
                        [InlineKeyboardButton('<-- De volta às configurações do canal', callback_data=f'home+{channel_id}')]
                    ]
                    await callback_query.edit_message_text(f'Legenda atual é : \n\n{caption} \n\nUse botões abaixo para alterá-lo ou removê-lo.', reply_markup=InlineKeyboardMarkup(buttons))
                else:
                    buttons = [
                        [InlineKeyboardButton('Adicionar Legenda', callback_data=f'add+{change}+{channel_id}')],
                        [InlineKeyboardButton('<-- Voltar para inicial', callback_data=f'home+{channel_id}')]
                    ]
                    await callback_query.edit_message_text(f'Sem legendas definidas \n\nUse o botão abaixo para adicioná-lo.', reply_markup=InlineKeyboardMarkup(buttons))
            elif change == 'buttons':
                if buttons:
                    _buttons = [
                        [InlineKeyboardButton('Alterar botões de URL', callback_data=f'add+{change}+{channel_id}')],
                        [InlineKeyboardButton('Remover botões de URL', callback_data=f'remove+{change}+{channel_id}')],
                        [InlineKeyboardButton('<-- De volta às configurações do canal', callback_data=f'home+{channel_id}')]
                    ]
                    await callback_query.edit_message_text(f'Botões atuais são : \n\n`{buttons}` \n\nUse botões abaixo para alterá-lo ou removê-lo.', reply_markup=InlineKeyboardMarkup(_buttons))
                else:
                    _buttons = [
                        [InlineKeyboardButton('Adicionar Botões', callback_data=f'add+{change}+{channel_id}')],
                        [InlineKeyboardButton('<-- Voltar para configuração do canal', callback_data=f'home+{channel_id}')]
                    ]
                    await callback_query.edit_message_text(f'Sem botões definidos \n\nUse o botão abaixo para adicioná-los.', reply_markup=InlineKeyboardMarkup(_buttons))
            elif change == 'position':
                current_position = query.split('+')[3]
                if current_position == 'below':
                    new_position = 'above'
                elif current_position == 'above':
                    new_position = 'replace'
                else:
                    new_position = 'below'
                await set_position(channel_id, new_position)
                text, markup, __ = await channel_settings(channel_id, bot)
                if text:
                    await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                else:
                    await callback_query.answer("Canal não existe no banco de dados", show_alert=True)
                    await callback_query.message.delete()
            elif change == 'edit_mode':
                current_edit_mode = query.split('+')[3]
                if current_edit_mode == 'all':
                    new_edit_mode = 'media'
                else:
                    new_edit_mode = 'all'
                await set_edit_mode(channel_id, new_edit_mode)
                text, markup, __ = await channel_settings(channel_id, bot)
                if text:
                    await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                else:
                    await callback_query.answer("Canal não existe no banco de dados", show_alert=True)
                    await callback_query.message.delete()
            elif change == 'sticker':
                if sticker_id:
                    buttons = [
                        [InlineKeyboardButton('Mostrar adesivo atual', callback_data=f'show+{channel_id}')],
                        [InlineKeyboardButton('Alterar adesivo', callback_data=f'add+{change}+{channel_id}')],
                        [InlineKeyboardButton('Remover adesivo', callback_data=f'remove+{change}+{channel_id}')],
                        [InlineKeyboardButton('<-- De volta às configurações do canal', callback_data=f'home+{channel_id}')]
                    ]
                    await callback_query.edit_message_text(f'Um adesivo já está definido. Veja tocando \'Show Current Sticker\' botão \n\nUse botões abaixo para alterá-lo ou removê-lo.', reply_markup=InlineKeyboardMarkup(buttons))
                else:
                    buttons = [
                        [InlineKeyboardButton('Adicionar Sticker', callback_data=f'add+{change}+{channel_id}')],
                        [InlineKeyboardButton('<-- Voltar para configuração do canal', callback_data=f'home+{channel_id}')]
                    ]
                    await callback_query.edit_message_text(f'Sem conjunto de adesivos \n\nUse o botão abaixo para adicioná-lo.', reply_markup=InlineKeyboardMarkup(buttons))
            elif change == 'webpage_preview':
                current = query.split('+')[3]
                if current.lower() == 'true':
                    new = False
                else:
                    new = True
                await toggle_webpage_preview(channel_id, new)
                text, markup, __ = await channel_settings(channel_id, bot)
                if text:
                    await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                else:
                    await callback_query.answer("Canal não existe no banco de dados", show_alert=True)
                    await callback_query.message.delete()
    elif query.startswith('add'):
        add = query.split('+')[1]
        channel_id = int(query.split('+')[2])
        try:
            if add == 'caption':
                data = await bot.ask(user_id, 'Por favor, envie a nova legenda ou /cancel o processo. Qualquer coisa que você enviar agora será definida como legenda, então tenha cuidado !', timeout=300)
                if data.text.lower() == '/cancel':
                    await data.reply('Cancelado', quote=True)
                else:
                    await set_caption(channel_id, data.text.markdown)
                    await data.reply('Legenda adicionado com sucesso !', quote=True)
                    text, markup, sticker_id = await channel_settings(channel_id, bot)
                    if sticker_id:
                        await callback_query.message.reply_sticker(sticker_id)
                    if text:
                        await callback_query.message.delete()
                        await callback_query.message.reply(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                    else:
                        await callback_query.answer('Canal Não Encontrado. Por favor, adicione novamente !', show_alert=True)
                        await crc(channel_id)
                        await urc(user_id, channel_id)
                        await callback_query.message.delete()
            elif add == 'buttons':
                data = await bot.ask(
                    user_id,
                    "**Formato de botões:** \n\n"
                    "Um botão deve ter um texto e uma url separado por '`-`'. \nSeu texto - link\n"
                    "Exemplo: \n`Google - google.com` \n\n"
                    "Para vários botões em uma única linha, use '`|`' Escreva-os em uma linha!!. \ntexto1 - link1 | texto2 - link2\n"
                    "Exemplo: \n`Google - google.com | Telegram - telegram.org`. \n"
                    "Para várias linhas, escreva-as em diferentes linhas. \ntexto1 - link1\ntexto2 - link2\n"
                    "Exemplo: \n`Google - google.com \n"
                    "Telegram - telegram.org | Change - change.org \n"
                    "Wikipedia - wikipedia.org` \n\n\n"
                    "Agora, por favor. **enviar os botões que tu queira no canal embaixo das tuas postagens** ou /cancel o processo. \n\n",
                    timeout=300
                )
                while True:
                    if data.text == '/cancel':
                        await data.reply('Cancelado', quote=True)
                        break
                    if "-" not in data.text:
                        data = await bot.ask(user_id, 'Formato errado para botões! Por favor, tente de novo..',
                                             timeout=300)
                    else:
                        given_buttons = await string_to_buttons(data.text)
                        try:
                            await data.reply('Como eles vão ficar !', reply_markup=InlineKeyboardMarkup(given_buttons))
                            await set_buttons(channel_id, data.text)
                            await data.reply('Botões definidos com sucesso !', quote=True)
                            text, markup, sticker_id = await channel_settings(channel_id, bot)
                            if sticker_id:
                                await callback_query.message.reply_sticker(sticker_id)
                            if text:
                                await callback_query.message.delete()
                                await callback_query.message.reply(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                            else:
                                await callback_query.answer('Canal Não Encontrado. Por favor, adicione novamente !', show_alert=True)
                                await crc(channel_id)
                                await urc(user_id, channel_id)
                                await callback_query.message.delete()
                            break
                        except ButtonUrlInvalid:
                            data = await bot.ask(user_id, 'Formato errado para botões! Por favor, tente de novo.', timeout=300)
            elif add == 'position':
                # Won't happen
                pass
            elif add == 'edit_mode':
                # Won't happen
                pass
            elif add == 'sticker':
                data = await bot.ask(user_id, 'Por favor, envie um adesivo.', timeout=300, filters=filters.sticker)
                await set_sticker(channel_id, data.sticker.file_id)
                await data.reply('Adesivo selecionado com sucesso !', quote=True)
                text, markup, sticker_id = await channel_settings(channel_id, bot)
                if sticker_id:
                    await callback_query.message.reply_sticker(sticker_id)
                if text:
                    await callback_query.message.delete()
                    await callback_query.message.reply(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                else:
                    await callback_query.answer('Canal Não Encontrado. Por favor, adicione novamente !', show_alert=True)
                    await crc(channel_id)
                    await urc(user_id, channel_id)
                    await callback_query.message.delete()
            elif add == 'webpage_preview':
                # Won't happen
                pass
        except asyncio.exceptions.TimeoutError:
            pass
    elif query.startswith('remove'):
        args = query.split('+')
        if len(args) == 2:
            channel_id = int(args[1])
            await crc(channel_id)
            await urc(user_id, channel_id)
            await callback_query.answer('Canal removido com sucesso', show_alert=True)
            success, buttons, text = await manage_channels(user_id, bot)
            if success:
                await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await callback_query.edit_message_text('Sem canais encontrados')
        else:
            remove = args[1]
            channel_id = int(args[2])
            if remove == 'caption':
                await set_caption(channel_id, None)
                await callback_query.answer('Legenda removida com sucesso !', show_alert=True)
                text, markup, sticker_id = await channel_settings(channel_id, bot)
                if sticker_id:
                    await callback_query.message.reply_sticker(sticker_id)
                if text:
                    await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                else:
                    await callback_query.answer('Canal Não Encontrado. Por favor, adicione novamente !', show_alert=True)
                    await crc(channel_id)
                    await urc(user_id, channel_id)
                    await callback_query.message.delete()
            elif remove == 'buttons':
                await set_buttons(channel_id, None)
                await callback_query.answer('Botões removidos com sucesso !', show_alert=True)
                text, markup, sticker_id = await channel_settings(channel_id, bot)
                if sticker_id:
                    await callback_query.message.reply_sticker(sticker_id)
                if text:
                    await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                else:
                    await callback_query.answer('Canal Não Encontrado. Por favor, adicione novamente !', show_alert=True)
                    await crc(channel_id)
                    await urc(user_id, channel_id)
                    await callback_query.message.delete()
            elif remove == 'position':
                # Won't happen
                pass
            elif remove == 'edit_mode':
                # Won't happen
                pass
            elif remove == 'sticker':
                await set_sticker(channel_id, None)
                await callback_query.answer('Sticker removido com sucesso !', show_alert=True)
                text, markup, sticker_id = await channel_settings(channel_id, bot)
                if sticker_id:
                    await callback_query.message.reply_sticker(sticker_id)
                if text:
                    await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(markup), disable_web_page_preview=True)
                else:
                    await callback_query.answer('Canal Não Encontrado. Por favor, adicione novamente !', show_alert=True)
                    await crc(channel_id)
                    await urc(user_id, channel_id)
                    await callback_query.message.delete()
            elif remove == 'webpage_preview':
                # Won't happen
                pass
    elif query.startswith('show'):
        channel_id = int(query.split('+')[1])
        sticker_id = await get_sticker(channel_id)
        if sticker_id:
            sticker = await callback_query.message.reply_sticker(sticker_id)
            await sticker.reply('Este é o adesivo atual', quote=True)
        else:
            await callback_query.answer('Canal Não Encontrado.', show_alert=True)
            await callback_query.message.delete()
