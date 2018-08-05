#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Scorebot Scoring Django Models

from math import floor
from scorebot import Scoring, Default
from scorebot.util import new
from django.utils.timezone import now
from scorebot.constants import CORRECTION_REASONS
from django.db.models import Model, SET_NULL, ForeignKey, CASCADE, OneToOneField, DateTimeField, IntegerField, \
                             BooleanField, PositiveSmallIntegerField


class Transaction(Model):
    class Meta:
        verbose_name = '[Score] Transaction'
        verbose_name_plural = '[Score] Transaction'

    value = IntegerField('Transaction Value', default=0)
    when = DateTimeField('Transaction Date/Time', auto_now_add=True)
    previous = OneToOneField('self', null=True, blank=True, on_delete=SET_NULL)
    source = ForeignKey('scorebot_db.Team', on_delete=CASCADE, related_name='deductions')
    destination = ForeignKey('scorebot_db.Team', on_delete=CASCADE, related_name='transactions')

    def log(self):
        # Value, Type, ISO When, Path From, Path To, Score
        Scoring.info('%d,%s,%s,%s,%s,%d' % (
            self.get_score(), self.get_name(), self.when.isoformat(), self.source.get_path(),
            self.destination.get_path(), self.destination.get_score()
        ))

    def update(self):
        if self.previous is not None:
            return self.get_score() + self.previous.get_score()
        return self.get_score()

    def __str__(self):
        return self.__subclass__().__string__()

    def __len__(self):
        return abs(self.get_score())

    def __next__(self):
        return self.previous

    def __bool__(self):
        return self.get_score() > 0

    def __json__(self):
        return {
            'type': self.get_name(),
            'value': self.get_score(),
            'when': self.when.isoformat(),
            'source': self.source.get_name(),
            'destination': self.destination.get_name()
        }

    def get_name(self):
        return str(self.__subclass__().__class__.__name__)

    def get_json(self):
        return self.__subclass__().__json__()

    def get_score(self):
        return self.__subclass__().__score__()

    def __score__(self):
        return self.value

    def __string__(self):
        return '[Transaction] (%s) %d: %s -> %s' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.value, self.source.get_path(), self.destination.get_path()
        )

    def __subclass__(self):
        try:
            return self.payment
        except AttributeError:
            pass
        try:
            return self.transfer
        except AttributeError:
            pass
        try:
            return self.purchase
        except AttributeError:
            pass
        try:
            return self.correction
        except AttributeError:
            pass
        try:
            return self.paymenthealth
        except AttributeError:
            pass
        try:
            return self.transferresult
        except AttributeError:
            pass
        try:
            return self.transactionflag
        except AttributeError:
            pass
        try:
            return self.transactionbeacon
        except AttributeError:
            pass
        return self

    def __lt__(self, other):
        return isinstance(other, Transaction) and other.get_score() > self.get_score()

    def __gt__(self, other):
        return isinstance(other, Transaction) and other.get_score() < self.get_score()

    def __eq__(self, other):
        return isinstance(other, Transaction) and other.get_score() == self.get_score()

    def get_json_stack(self):
        total = 0
        score = self
        stack = list()
        while score is not None:
            stack.append(score.get_json())
            total += score.get_score()
            score = next(score)
        result = {
            'stack': stack,
            'total': total
        }
        del stack
        del total
        return result


class Payment(Transaction):
    class Meta:
        verbose_name = '[Score] Payment'
        verbose_name_plural = '[Score] Payments'

    target = ForeignKey('scorebot_db.PlayingTeam', on_delete=CASCADE, related_name='payments')

    def pay(self):
        payment = floor(float(self.get_score() * float((100 - self.target.deduction) / 100)))
        if payment < 0:
            payment = 0
        result = new('PaymentHealth', False)
        result.value = payment
        result.source = self.destination
        result.destination = self.target
        result.expected = self.get_score()
        result.save()
        self.target.add_transaction(result)
        Default.info('Payment from "%s" of "%d" via "%s" was issued to "%s" as "%d" (%d%% deduction).' % (
            self.source.get_path(), self.get_score(), self.destination.get_path(), self.target.get_path(), payment,
            self.target.deduction
        ))
        self.log()
        del result
        del payment

    def __json__(self):
        return {
            'type': self.get_name(),
            'value': self.get_score(),
            'when': self.when.isoformat(),
            'target': self.target.get_name(),
            'source': self.source.get_name(),
            'destination': self.destination.get_name()
        }

    def __string__(self):
        return '[Payment] (%s) %d PTS: %s -> %s (%s)' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.get_score(), self.source.get_path(), self.destination.get_path(),
            self.target.get_path()
        )


class Transfer(Transaction):
    class Meta:
        verbose_name = '[Score] Transfer'
        verbose_name_plural = '[Score] Transfer'

    processed = BooleanField('Tranfer Processed', default=False)
    approved = DateTimeField('Tansfer Approved', null=True, blank=True)

    def __score__(self):
        return self.value * -1

    def __string__(self):
        return '[Transfer] (%s) %d [%s] PTS: %s -> %s' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.value, 'Approved' if self.approved else 'Pending',
            self.source.get_path(), self.destination.get_path()
        )

    def set_approval(self, approve=True):
        self.approved = now()
        if not approve:
            Default.info('Score Transfer from "%s" of "%d" to "%s" was disapproved, funds were returned.' % (
                self.source.get_path(), self.value, self.destination.get_path()
            ))
            self.value = 0
        else:
            result = new('TransferResult', False)
            result.value = self.value
            result.source = self.source
            result.destination = self.destination
            result.save()
            result.destination.add_transaction(result)
            Default.info('Score Transfer from "%s" of "%d" to "%s" was approved.' % (
                self.source.get_path(), self.value, self.destination.get_path()
            ))
            del result
        self.log()
        self.source.update()
        self.processed = True
        self.save()


class Purchase(Transaction):
    class Meta:
        verbose_name = '[Score] Purchase'
        verbose_name_plural = '[Score] Purchases'

    item = ForeignKey('scorebot_db.Item', blank=True, null=True, on_delete=SET_NULL, related_name='purchases')

    def __json__(self):
        return {
            'type': self.get_name(),
            'value': self.get_score(),
            'item': self.item.get_name(),
            'when': self.when.isoformat(),
            'source': self.source.get_name(),
            'destination': self.destination.get_name()
        }

    def __score__(self):
        return self.value * -1

    def __string__(self):
        return '[Purchase] (%s) %s: %d PTS: %s' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.item.get_name(), self.value, self.source.get_path()
        )


class Correction(Transaction):
    class Meta:
        verbose_name = '[Score] Correction'
        verbose_name_plural = '[Score] Correction'

    reason = PositiveSmallIntegerField('Correction Reason', default=0, choices=CORRECTION_REASONS)

    def __json__(self):
        return {
            'type': self.get_name(),
            'value': self.get_score(),
            'when': self.when.isoformat(),
            'source': self.source.get_name(),
            'reason': self.get_reason_display(),
            'destination': self.destination.get_name()
        }

    def __string__(self):
        return '[Correction] (%s) %s %d PTS: %s -> %s' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.get_reason_display(), self.get_score(), self.source.get_path(),
            self.destination.get_path()
        )


class PaymentHealth(Transaction):
    class Meta:
        verbose_name = '[Score] Health Payment'
        verbose_name_plural = '[Score] Health Payments'

    expected = IntegerField('Expected Payment Value')

    def __json__(self):
        return {
            'type': self.get_name(),
            'value': self.get_score(),
            'expected': self.expected,
            'when': self.when.isoformat(),
            'source': self.source.get_name(),
            'destination': self.destination.get_name()
        }

    def __string__(self):
        if self.get_score() == 0:
            return '[PaymentHealth] (%s) %d/%d PTS: %s -> %s (%s%%)' % (
                self.when.strftime('%m/%d/%y %H:%M'), self.get_score(), self.expected, self.source.get_path(),
                self.destination.get_path(), 0
            )
        return '[PaymentHealth] (%s) %d/%d PTS: %s -> %s (%s%%)' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.get_score(), self.expected, self.source.get_path(),
            self.destination.get_path(), floor(float(self.expected / self.get_score()) * 100)
        )


class TransferResult(Transaction):
    class Meta:
        verbose_name = '[Score] Transfer Result'
        verbose_name_plural = '[Score] Transfer Result'

    def __string__(self):
        return '[TransferResult] (%s) %d PTS: %s -> %s' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.get_score(), self.source.get_path(), self.destination.get_path()
        )


class TransactionFlag(Transaction):
    class Meta:
        verbose_name = '[Score] Flag Transaction'
        verbose_name_plural = '[Score] Flag Transactions'

    flag = ForeignKey('scorebot_db.Flag', on_delete=CASCADE, related_name='transaction')

    def __json__(self):
        return {
            'type': self.get_name(),
            'value': self.get_score(),
            'flag': self.flag.get_name(),
            'when': self.when.isoformat(),
            'source': self.source.get_name(),
            'destination': self.destination.get_name()
        }

    def __string__(self):
        return '[TransactionFlag] (%s) %s: %d PTS: %s -> %s' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.flag.get_path(), self.get_score(), self.source.get_path(),
            self.destination.get_path()
        )


class TransactionBeacon(Transaction):
    class Meta:
        verbose_name = '[Score] Beacon Transaction'
        verbose_name_plural = '[Score] Beacon Transactions'

    beacon = ForeignKey('scorebot_db.Beacon', on_delete=CASCADE, related_name='transactions')

    def __json__(self):
        return {
            'type': self.get_name(),
            'value': self.get_score(),
            'when': self.when.isoformat(),
            'beacon': self.beacon.get_name(),
            'source': self.source.get_name(),
            'destination': self.destination.get_name()
        }

    def __string__(self):
        return '[TransactionBeacon] (%s) %s: %d PTS: %s -> %s' % (
            self.when.strftime('%m/%d/%y %H:%M'), self.beacon.get_path(), self.get_score(), self.source.get_path(),
            self.destination.get_path()
        )

# EOF
